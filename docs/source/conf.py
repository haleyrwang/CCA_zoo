# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import datetime

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import warnings

sys.path.insert(0, os.path.abspath("../.."))
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Matplotlib is currently using agg, which is a"
    " non-GUI backend, so cannot show the figure.",
)
# -- Project information -----------------------------------------------------

project = "CCA-Zoo"
author = "James Chapman"
copyright = f"{datetime.datetime.now().year}, {author}"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_gallery.gen_gallery",
]

sphinx_gallery_conf = {
    "doc_module": "cca-zoo",
    "examples_dirs": "../../examples",  # path to your example scripts
    "gallery_dirs": "auto_examples",  # path to where to save gallery generated output
    "ignore_pattern": "__init__.py",
}

# -- sphinx.ext.intersphinx
intersphinx_mapping = {
    "numpy": ("https://docs.scipy.org/doc/numpy", None),
    "python": ("https://docs.python.org/3", None),
    "sklearn": ("http://scikit-learn.org/dev", None),
    "torch": ("https://pytorch.org/docs/master", None),
    "pytorch_lightning": (
        "https://pytorch-lightning.readthedocs.io/en/stable/index.html#",
        None,
    ),
    "jax": ("https://jax.readthedocs.io/en/latest/", None),
    "numpyro": ("https://numpyro.readthedocs.io/en/latest/", None),
    "jaxlib": ("https://jax.readthedocs.io/en/latest/", None),
}

# -- sphinx.ext.autodoc
autodoc_member_order = "bysource"
autoclass_content = "both"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

master_doc = "index"
