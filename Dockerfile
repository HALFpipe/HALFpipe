ARG FMRIPREP_VERSION=20.1.0rc2

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

RUN pip install --upgrade pip && \
    pip install 'nibabel>=3.0.0' 'niworkflows~=1.1.3' cython 

RUN mkdir -p /root/src && \
  curl -sSL \
  $(curl -sSL "https://api.github.com/repos/mindandbrain/qualitycheck/releases/latest" \
  | grep browser_download_url | cut -d '"' -f 4) -o /root/src/qualitycheck.html 
  
RUN mkdir /ext
COPY . /root/src/pipeline/

RUN cd /root/src/pipeline && \
    cp /root/src/qualitycheck.html pipeline/index.html && \
    cp VERSION pipeline/VERSION && \
    pip install .[all] && \
    python postsetup.py && \
    rm -rf ~/.cache/pip && \
    cd .. && rm -rf /root/src/pipeline

ENTRYPOINT ["/usr/local/miniconda/bin/pipeline"]
