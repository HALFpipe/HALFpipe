ARG FMRIPREP_VERSION=20.1.1

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

ENV PATH="/usr/local/miniconda/bin:$PATH" \
    HALFPIPE_RESOURCE_DIR="/home/fmriprep/.cache/halfpipe" \
    TEMPLATEFLOW_HOME="/home/fmriprep/.cache/templateflow"
    
RUN mkdir /ext /halfpipe 

COPY . /halfpipe/

RUN cd /halfpipe && \
    pip install --upgrade pip && \
    pip uninstall --yes fmriprep smriprep mriqc niworkflows nipype statsmodels patsy && \
    pip install . && \
    python postsetup.py && \
    rm -rf ~/.cache/pip && \
    cd .. && rm -rf /root/src/halfpipe
    
ENTRYPOINT ["/usr/local/miniconda/bin/halfpipe"]
