#!/bin/sh
conda create -y -n ai python=3.12
conda activate ai
pip install --upgrade pip
pip install notebook jupyterlab
pip install nbclassic
conda install -c anaconda -y graphviz ply seaborn scikit-learn 
conda install -c conda-forge -y python-graphviz matplotlib ipycanvas 
pip install nb_mypy
pip install z3-solver
pip install git+https://github.com/reclinarka/problem_visuals
pip install git+https://github.com/reclinarka/chess-problem-visuals
pip install memory_profiler
# start notebook with jupyter nbclassic
