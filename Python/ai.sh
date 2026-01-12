conda create -n ai
conda activate ai
conda install -y -c conda-forge python=3.13 jupyter nbclassic
conda install -y -c conda-forge graphviz
conda install -y -c conda-forge python-graphviz
conda install -y -c conda-forge numpy matplotlib seaborn
conda install -y -c conda-forge scikit-learn 
conda install -y -c conda-forge ipycanvas 
pip install ply
pip install mypy
pip install nb-mypy
pip install z3-solver
pip install git+https://github.com/reclinarka/problem_visuals
pip install git+https://github.com/reclinarka/chess-problem-visuals



