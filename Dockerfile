ARG FMRIPREP_VERSION=1.0.9
ARG MRIQC_VERSION=0.10.4

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

ARG MRIQC_VERSION

RUN mkdir -p /root/src/mriqc && \
    curl -sSL "https://api.github.com/repos/poldracklab/mriqc/tarball/${MRIQC_VERSION}" \
    | tar -xzC /root/src/mriqc --strip-components 1 && \
    cd /root/src/mriqc && \
    pip install -r requirements.txt && \
    pip install .[all] && \
    rm -rf ~/.cache/pip 

COPY . /root/src/pipeline
RUN cd /root/src/pipeline && \
    pip install .[all] && \
    rm -rf ~/.cache/pip

ENTRYPOINT ["/usr/local/miniconda/bin/pipeline"]