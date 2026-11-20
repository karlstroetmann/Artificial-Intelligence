conda create -n knights
conda activate knights
conda install -y -c conda-forge python=3.14 jupyterlab
conda install -y -c conda-forge graphviz python-graphviz  # draws the graph of knight moves
pip install nb-mypy                                       # %load_ext nb_mypy, installs mypy as well
