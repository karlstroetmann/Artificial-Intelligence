#!/bin/bash
conda create -y -n ai python=3.7 jupyter notebook
source activate ai
conda install -y "nbconvert=5.6.1"
conda install -y -c conda-forge jupyter_contrib_nbextensions
conda install -y -c anaconda graphviz
conda install -y -c conda-forge python-graphviz
conda install -y -c anaconda ply
conda install -y -c conda-forge ipycanvas
pip install jedi==0.17.2
pip install python-chess
