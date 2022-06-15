#!/bin/bash
conda create -y -n ai python=3.10 
conda activate ai
conda install -c anaconda -y graphviz ply seaborn scikit-learn 
conda install -c conda-forge -y python-graphviz ipycanvas matplotlib memory_profiler autograd jupyter notebook
pip install chess 
pip install nbimporter

