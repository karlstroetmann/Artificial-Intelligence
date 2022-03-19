#!/bin/bash
conda create -y -n ai python=3 jupyter notebook
conda activate ai
conda install -c anaconda -y graphviz ply seaborn scikit-learn keras tensorflow
conda install -c conda-forge -y python-graphviz ipycanvas matplotlib memory_profiler
pip install chess 

