"""
Model Plotting
===========================

This script will show how to use the plotting functions of the CCA-Zoo package.
"""

import numpy as np
from sklearn.model_selection import train_test_split

from cca_zoo import CCA
from cca_zoo.data import linear_simulated_data
import matplotlib.pyplot as plt

from cca_zoo.plotting import pairplot_train_test


# Data
# ------
np.random.seed(42)
n = 200
p = 25
q = 25
latent_dims = 3

(X, Y), (tx, ty) = linear_simulated_data(
    n, view_features=[p, q], latent_dims=latent_dims, correlation=[0.9, 0.8, 0.7]
)

X_tr, X_te, Y_tr, Y_te = train_test_split(X, Y, test_size=0.2, random_state=42)

# %%
# Model
# ------

cca = CCA(latent_dims=latent_dims).fit((X_tr, Y_tr))

#%%
# Plotting
# ---------

pairplot_train_test(cca.transform((X_tr, Y_tr)), cca.transform((X_te, Y_te)))
plt.show()