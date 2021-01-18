ARG FMRIPREP_VERSION=20.2.1
FROM nipreps/fmriprep:${FMRIPREP_VERSION}

LABEL org.opencontainers.image.source https://github.com/HALFpipe/HALFpipe
LABEL org.opencontainers.image.documentation="https://github.com/HALFpipe/HALFpipe/blob/master/README.md"

ENV PATH="/usr/local/miniconda/bin:$PATH" \
    HALFPIPE_RESOURCE_DIR="/home/fmriprep/.cache/halfpipe" \
    TEMPLATEFLOW_HOME="/home/fmriprep/.cache/templateflow"

RUN pip install --upgrade pip && \
    pip uninstall --yes fmriprep smriprep mriqc niworkflows nipype statsmodels patsy matplotlib

RUN mkdir /ext /halfpipe 

COPY requirements.txt /halfpipe/
RUN cd /halfpipe && \
    pip install -r requirements.txt

COPY postsetup.py halfpipe/resource.py /halfpipe/
RUN cd /halfpipe && \
    python postsetup.py

COPY . /halfpipe/
RUN cd /halfpipe && \
    pip install . && \
    rm -rf ~/.cache/pip && \
    cd .. && rm -rf /halfpipe/*
    
ENTRYPOINT ["/usr/local/miniconda/bin/halfpipe"]
