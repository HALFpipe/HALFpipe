ARG FMRIPREP_VERSION=20.1.1

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

ENV PATH="/usr/local/miniconda/bin:$PATH" \
    PIPELINE_RESOURCE_DIR="/home/fmriprep/.cache/pipeline" \
    TEMPLATEFLOW_HOME="/home/fmriprep/.cache/templateflow"
    
RUN mkdir /ext /pipeline 

COPY . /pipeline/

RUN cd /pipeline && \
    pip install --upgrade pip && \
    pip install .[all] && \
    python postsetup.py && \
    rm -rf ~/.cache/pip && \
    cd .. && rm -rf /root/src/pipeline
    
ENTRYPOINT ["/usr/local/miniconda/bin/pipeline"]
