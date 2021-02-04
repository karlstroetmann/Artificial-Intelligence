FROM jupyter/minimal-notebook

MAINTAINER "Christian Gommans <info@cgweb.net>"

ARG conda_env=ai

COPY --chown=${NB_UID}:${NB_GID} Python/. /home/$NB_USER/stroetmann-data/
COPY --chown=${NB_UID}:${NB_GID} Docker/env.yml /home/$NB_USER/tmp/

RUN cd /home/$NB_USER/tmp/ && \
	conda env create -p $CONDA_DIR/envs/$conda_env -f env.yml && \
    conda clean --all -f -y

RUN $CONDA_DIR/envs/${conda_env}/bin/python -m ipykernel install --user --name=${conda_env} && \
    fix-permissions $CONDA_DIR && \
    fix-permissions /home/$NB_USER

ENV PATH $CONDA_DIR/envs/${conda_env}/bin:$PATH

ENV CONDA_DEFAULT_ENV ${conda_env}
ENV PYTHONHASHSEED=0

EXPOSE 8888

ENTRYPOINT ["jupyter", "notebook", "--no-browser", "--ip=0.0.0.0", "--NotebookApp.token=''", "--NotebookApp.password=''","--NotebookApp.iopub_msg_rate_limit=1e10"]