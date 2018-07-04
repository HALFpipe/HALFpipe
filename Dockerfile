ARG FMRIPREP_VERSION=1.0.15
ARG MRIQC_VERSION=0.10.4

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

# ENV HTTP_PROXY http://141.42.1.215:8080
# ENV HTTPS_PROXY http://141.42.1.215:8080

ARG MRIQC_VERSION

RUN mkdir -p /root/src/mriqc && \
    curl -sSL "https://api.github.com/repos/poldracklab/mriqc/tarball/${MRIQC_VERSION}" \
    | tar -xzC /root/src/mriqc --strip-components 1 && \
    cd /root/src/mriqc && \
    pip install -r requirements.txt && \
    pip install .[all] && \
    rm -rf ~/.cache/pip 

RUN mkdir /ext

COPY . /root/src/pipeline
RUN cd /root/src/pipeline && \
    pip install .[all] && \
    rm -rf ~/.cache/pip

ENTRYPOINT ["/usr/local/miniconda/bin/pipeline"]
