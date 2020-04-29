Bootstrap: docker
From: poldracklab/fmriprep:20.1.0rc2

%setup
  mkdir -p ${SINGULARITY_ROOTFS}/pipeline
  mkdir -p ${SINGULARITY_ROOTFS}/ext

%files
  . /pipeline

%post
  chmod -R a+rwx /pipeline /usr/local/miniconda
  
  su -c 'export PATH=/usr/local/miniconda/bin:$PATH && \
    cd /pipeline && \
    pip install --upgrade pip && \
    pip install . && \
    python postsetup.py' fmriprep
  
  rm -rf ~/.cache/pip
  rm -rf /root/src/pipeline

%runscript
  exec /usr/local/miniconda/bin/pipeline "$@"
  
%startscript
  exec /usr/local/miniconda/bin/pipeline "$@"
