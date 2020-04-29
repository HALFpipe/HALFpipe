ARG FMRIPREP_VERSION=20.1.0rc2

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

ENV PATH="/usr/local/miniconda/bin:$PATH"

COPY . /root/src/pipeline/

RUN cd /root/src/pipeline && \
    pip install --upgrade pip && \
    pip install .[all] && \
    python postsetup.py && \
    rm -rf ~/.cache/pip && \
    cd .. && rm -rf /root/src/pipeline
    
RUN mkdir /ext

ENTRYPOINT ["/usr/local/miniconda/bin/pipeline"]
