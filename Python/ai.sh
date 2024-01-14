#!/bin/bash
conda create -y -n ai python=3.11 jupyter
conda activate ai
conda install -c anaconda -y nbclassic graphviz ply seaborn scikit-learn 
conda install -c conda-forge -y python-graphviz matplotlib memory_profiler autograd ipycanvas 
python3 -m pip install nb_mypy
python3 -m pip install chess 
pip install z3-solver
