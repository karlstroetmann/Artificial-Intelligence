#!/bin/bash
conda create -y -n ai python=3 jupyter notebook
source activate ai
conda install -y -c anaconda graphviz
conda install -y -c conda-forge python-graphviz
conda install -y -c anaconda ply
conda install -y -c conda-forge ipycanvas
conda install -y -c conda-forge matplotlib
conda install -y -c anaconda seaborn
conda install -y -c anaconda scikit-learn
pip install chess

