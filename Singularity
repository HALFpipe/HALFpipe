Bootstrap: docker
From: poldracklab/fmriprep:20.1.0rc2

%environment
  export PIPELINE_RESOURCE_DIR="/home/fmriprep/.cache/pipeline"
  export TEMPLATEFLOW_HOME="/home/fmriprep/.cache/templateflow"

%setup
  mkdir -p ${SINGULARITY_ROOTFS}/pipeline
  mkdir -p ${SINGULARITY_ROOTFS}/ext

%files
  . /pipeline

%post
  BUILD=11

  chmod -R a+rwx /pipeline /usr/local/miniconda
  
  su -c 'export PATH=/usr/local/miniconda/bin:$PATH && \
    cd /pipeline && \
    pip install --upgrade pip && \
    pip install . && \
    python postsetup.py' fmriprep
  
  rm -rf ~/.cache/pip

%runscript
  exec /usr/local/miniconda/bin/pipeline "$@"
  
%startscript
  exec /usr/local/miniconda/bin/pipeline "$@"
