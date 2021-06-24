import copy
import itertools
from typing import Union, Iterable

import numpy as np
import torch
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

import cca_zoo.utils.plot_utils
from cca_zoo.deepmodels.dcca import _DCCA_base
from cca_zoo.models import _CCA_Base


class DeepWrapper(_CCA_Base):
    """
    This class is used as a wrapper for DCCA, DCCAE, DVCCA, DTCCA, SplitAE. It can be inherited and adapted to
    customise the training loop. By inheriting _CCA_Base, the DeepWrapper class gives access to fit_transform.
    """

    def __init__(self, model: _DCCA_base, device: str = 'cuda', tensorboard: bool = False, tensorboard_tag: str = '',
                 optimizer: torch.optim.Optimizer = None, scheduler=None, lr=1e-3, clip_value=float('inf')):
        """

        :param model: a
        :param device:
        :param tensorboard:
        :param tensorboard_tag:
        :param optimizer:
        :param scheduler:
        :param lr:
        :param clip_value:
        """
        super().__init__(latent_dims=model.latent_dims)
        self.model = model
        self.device = device
        if not torch.cuda.is_available() and self.device == 'cuda':
            self.device = 'cpu'
        self.latent_dims = model.latent_dims
        self.tensorboard = tensorboard
        if tensorboard:
            self.writer = SummaryWriter(tensorboard_tag)
        if optimizer is None:
            # Andrew G, Arora R, Bilmes J, Livescu K. Deep canonical correlation analysis. InInternational conference on machine learning 2013 May 26 (pp. 1247-1255). PMLR.
            self.optimizer = torch.optim.LBFGS(self.model.parameters(), lr=lr)
        self.scheduler = scheduler
        self.clip_value = clip_value

    def fit(self, train_dataset: Union[torch.utils.data.Dataset, Iterable[np.ndarray]],
            val_dataset: Union[torch.utils.data.Dataset, Iterable[np.ndarray]] = None, train_labels=None,
            val_labels=None, val_split: float = 0,
            batch_size: int = 0, val_batch_size: int = 0,
            patience: int = 0, epochs: int = 1,
            train_correlations: bool = True):
        """

        :param train_dataset: either tuple of 2d numpy arrays (one for each view) or torch dataset
        :param val_dataset: either tuple of 2d numpy arrays (one for each view), torch dataset or None
        :param train_labels:
        :param val_labels:
        :param val_split: if val_dataset is None,
        :param batch_size: the minibatch size
        :param patience: if 0 train to num_epochs, else if validation score doesn't improve after patience epochs stop training
        :param epochs: maximum number of epochs to train
        :param train_correlations: if True generate training correlations
        :return:
        """
        train_dataset, val_dataset = self.process_data(train_dataset, val_dataset, train_labels, val_labels, val_split)

        if batch_size == 0:
            train_dataloader = DataLoader(train_dataset, batch_size=len(train_dataset))
        else:
            train_dataloader = DataLoader(train_dataset, batch_size=batch_size, drop_last=True)
        if val_dataset:
            if val_batch_size == 0:
                val_dataloader = DataLoader(val_dataset, batch_size=len(val_dataset))
            else:
                val_dataloader = DataLoader(val_dataset, batch_size=val_batch_size, drop_last=True)

        num_params = sum(p.numel() for p in self.model.parameters())
        print('total parameters: ', num_params)
        best_model = copy.deepcopy(self.model.state_dict())
        self.model.float().to(self.device)

        min_val_loss = torch.tensor(np.inf)
        epochs_no_improve = 0
        early_stop = False

        for epoch in range(1, epochs + 1):
            if not early_stop:
                # Train
                epoch_train_loss = self.train_epoch(train_dataloader)
                print('====> Epoch: {} Average train loss: {:.4f}'.format(
                    epoch, epoch_train_loss))
                if self.tensorboard:
                    self.writer.add_scalar('Loss/train', epoch_train_loss, epoch)
                # Val
                if val_dataset:
                    epoch_val_loss = self.val_epoch(val_dataloader)
                    if self.tensorboard:
                        self.writer.add_scalar('Loss/test', epoch_val_loss, epoch)
                    print('====> Epoch: {} Average val loss: {:.4f}'.format(
                        epoch, epoch_val_loss))
                    if epoch_val_loss < min_val_loss or epoch == 1:
                        min_val_loss = epoch_val_loss
                        best_model = copy.deepcopy(self.model.state_dict())
                        print('Min loss %0.2f' % min_val_loss)
                        epochs_no_improve = 0
                    else:
                        epochs_no_improve += 1
                        # Check early stopping condition
                        if epochs_no_improve == patience and patience > 0:
                            print('Early stopping!')
                            early_stop = True
                            self.model.load_state_dict(best_model)
                # Scheduler step
                if self.model.scheduler:
                    try:
                        self.model.scheduler.step()
                    except:
                        self.model.scheduler.step(epoch_train_loss)
        if self.tensorboard:
            self.writer.close()
        if train_correlations:
            self.train_correlations = self.predict_corr(train_dataset, train=True)
        return self

    def train_epoch(self, train_dataloader: torch.utils.data.DataLoader):
        """
        Train a single epoch
        :param train_dataloader: a dataloader for training data
        :return: average loss over the epoch
        """
        self.model.train()
        train_loss = 0
        for batch_idx, (data, label) in enumerate(train_dataloader):
            data = [d.float().to(self.device) for d in list(data)]
            loss = self.model.update_weights(*data)
            train_loss += loss.item()
        return train_loss / len(train_dataloader)

    def update_weights(self, *args):
        """
        A complete update of the weights used every batch
        :param args: batches for each view separated by commas
        :return:
        """
        if type(self.optimizer) == torch.optim.LBFGS:
            def closure():
                """
                Required by LBFGS optimizer
                """
                self.optimizer.zero_grad()
                loss = self.model.loss(*args)
                loss.backward()
                return loss

            torch.nn.utils.clip_grad_value_(self.model.parameters(), clip_value=self.clip_value)
            self.optimizer.step(closure)
            loss = closure()
        else:
            self.optimizer.zero_grad()
            loss = self.model.loss(*args)
            loss.backward()
            torch.nn.utils.clip_grad_value_(self.model.parameters(), clip_value=self.clip_value)
            self.optimizer.step()
        return loss

    def val_epoch(self, val_dataloader: torch.utils.data.DataLoader):
        """
        Validate a single epoch
        :param val_dataloader: a dataloder for validation data
        :return: average validation loss over the epoch
        """
        self.model.eval()
        for param in self.model.parameters():
            param.grad = None
        total_val_loss = 0
        for batch_idx, (data, label) in enumerate(val_dataloader):
            data = [d.float().to(self.device) for d in list(data)]
            loss = self.model.loss(*data)
            total_val_loss += loss.item()
        return total_val_loss / len(val_dataloader)

    def predict_corr(self, test_dataset: Union[torch.utils.data.Dataset, Iterable[np.ndarray]], train: bool = False,
                     batch_size: int = 0):
        """
        :param views: EITHER numpy arrays separated by comma. Each view needs to have the same number of features as its
         corresponding view in the training dataOR torch.torch.utils.data.Dataset
        :return: numpy array containing correlations between each pair of views for each dimension (#views*#views*#latent_dimensions)
        """
        transformed_views = self.transform(test_dataset, train=train, batch_size=batch_size)
        all_corrs = []
        for x, y in itertools.product(transformed_views, repeat=2):
            all_corrs.append(np.diag(np.corrcoef(x.T, y.T)[:x.shape[1], y.shape[1]:]))
        all_corrs = np.array(all_corrs).reshape(
            (len(transformed_views), len(transformed_views), -1))
        return all_corrs

    def transform(self, test_dataset: Union[torch.utils.data.Dataset, Iterable[np.ndarray]], test_labels=None,
                  train: bool = False, batch_size: int = 0):
        test_dataset = self.process_data(test_dataset, labels=test_labels)[0]
        if batch_size > 0:
            test_dataloader = DataLoader(test_dataset, batch_size=batch_size)
        else:
            test_dataloader = DataLoader(test_dataset, batch_size=len(test_dataset))
        with torch.no_grad():
            for batch_idx, (data, label) in enumerate(test_dataloader):
                data = [d.float().to(self.device) for d in list(data)]
                z = self.model(*data)
                if batch_idx == 0:
                    z_list = [z_i.detach().cpu().numpy() for i, z_i in enumerate(z)]
                else:
                    z_list = [np.append(z_list[i], z_i.detach().cpu().numpy(), axis=0) for
                              i, z_i in enumerate(z)]
        z_list = self.model.post_transform(*z_list, train=train)
        return z_list

    def predict_view(self, test_dataset: Union[torch.utils.data.Dataset, Iterable[np.ndarray]], test_labels=None):
        test_dataset = self.process_data(test_dataset, labels=test_labels)[0]
        test_dataloader = DataLoader(test_dataset, batch_size=len(test_dataset))
        with torch.no_grad():
            for batch_idx, (data, label) in enumerate(test_dataloader):
                data = [d.float().to(self.device) for d in list(data)]
                x = self.model.recon(*data)
                if batch_idx == 0:
                    x_list = [x_i.detach().cpu().numpy() for i, x_i in enumerate(x)]
                else:
                    x_list = [np.append(x_list[i], x_i.detach().cpu().numpy(), axis=0) for
                              i, x_i in enumerate(x)]
        return x_list

    def process_data(self, dataset: Union[torch.utils.data.Dataset, Iterable[np.ndarray]],
                     val_dataset: Union[torch.utils.data.Dataset, Iterable[np.ndarray]] = None, labels=None,
                     val_labels=None, val_split: float = 0):
        # Ensure datasets are in the right form (e.g. if numpy arrays are passed turn them into
        if isinstance(dataset, tuple):
            dataset = cca_zoo.data.CCA_Dataset(*dataset, labels=labels)
        if val_dataset is None and val_split > 0:
            lengths = [len(dataset) - int(len(dataset) * val_split), int(len(dataset) * val_split)]
            dataset, val_dataset = torch.utils.data.random_split(dataset, lengths)
        elif isinstance(val_dataset, tuple):
            val_dataset = cca_zoo.data.CCA_Dataset(*val_dataset, labels=val_labels)
        return dataset, val_dataset
