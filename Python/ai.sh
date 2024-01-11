#!/bin/bash
conda create -y -n ai python=3.12 
conda activate ai
conda install -c anaconda -y graphviz ply seaborn scikit-learn 
conda install -c conda-forge -y jupyter python-graphviz matplotlib memory_profiler autograd 
pip install ipycanvas
pip install chess 
pip install z3-solver
