ARG FMRIPREP_VERSION=20.2.0

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

ENV PATH="/usr/local/miniconda/bin:$PATH" \
    HALFPIPE_RESOURCE_DIR="/home/fmriprep/.cache/halfpipe" \
    TEMPLATEFLOW_HOME="/home/fmriprep/.cache/templateflow"
    
RUN mkdir /ext /halfpipe 

COPY . /halfpipe/

RUN cd /halfpipe && \
    pip install --upgrade pip && \
    pip uninstall --yes fmriprep smriprep mriqc niworkflows nipype statsmodels patsy matplotlib && \
    pip install --use-feature=2020-resolver . && \
    python postsetup.py && \
    rm -rf ~/.cache/pip && \
    cd .. && rm -rf /halfpipe
    
ENTRYPOINT ["/usr/local/miniconda/bin/halfpipe"]
