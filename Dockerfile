ARG FMRIPREP_VERSION=1.1.6
ARG MRIQC_VERSION=0.14.2
ARG CPAC_VERSION=v1.3.0

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

# ENV HTTP_PROXY http://141.42.1.215:8080
# ENV HTTPS_PROXY https://141.42.1.215:8080

ARG MRIQC_VERSION

RUN mkdir -p /root/src/mriqc && \
    curl -sSL "https://api.github.com/repos/poldracklab/mriqc/tarball/${MRIQC_VERSION}" \
    | tar -xzC /root/src/mriqc --strip-components 1 && \
    cd /root/src/mriqc && \
    pip install -r requirements.txt && \
    pip install .[all] && \
    rm -rf ~/.cache/pip

 RUN apt-get update && \
     apt-get install -y graphviz \
       graphviz-dev

RUN mkdir /ext

COPY . /root/src/pipeline/

RUN curl -sSL \
  $(curl -sSL "https://api.github.com/repos/mindandbrain/qualitycheck/releases/latest" \
  | grep browser_download_url | cut -d '"' -f 4) -o /root/src/pipeline/index.html 
  
RUN cd /root/src/pipeline && \
    cp VERSION index.html pipeline && \
    python setup.py install && \
    rm -rf ~/.cache/pip && \
    cd .. && rm -rf /root/src/pipeline

ENTRYPOINT ["/usr/local/miniconda/bin/pipeline"]
