Bootstrap: docker
From: poldracklab/fmriprep:20.1.1

%environment
  export HALFPIPE_RESOURCE_DIR="/home/fmriprep/.cache/halfpipe"
  export TEMPLATEFLOW_HOME="/home/fmriprep/.cache/templateflow"

%setup
  mkdir -p ${SINGULARITY_ROOTFS}/halfpipe
  mkdir -p ${SINGULARITY_ROOTFS}/ext

%files
  . /halfpipe

%post
  BUILD=74

  chmod -R a+rwx /halfpipe /usr/local/miniconda
  
  su -c 'export PATH=/usr/local/miniconda/bin:$PATH && \
    cd /halfpipe && \
    pip install --upgrade pip && \
    pip uninstall --yes fmriprep niworkflows nipype statsmodels patsy && \
    pip install . && \
    python postsetup.py' fmriprep
  
  rm -rf ~/.cache/pip

%runscript
  exec /usr/local/miniconda/bin/halfpipe "$@"
  
%startscript
  exec /usr/local/miniconda/bin/halfpipe "$@"
