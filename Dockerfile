ARG FMRIPREP_VERSION=20.2.3
FROM nipreps/fmriprep:${FMRIPREP_VERSION}

ENV PATH="/usr/local/miniconda/bin:$PATH" \
    XDG_CACHE_HOME="/home/fmriprep/.cache"

ENV HALFPIPE_RESOURCE_DIR="${XDG_CACHE_HOME}/halfpipe" \
    TEMPLATEFLOW_HOME="${XDG_CACHE_HOME}/templateflow"

RUN mkdir /ext /halfpipe && \
    chmod a+rwx /ext /halfpipe

# install dependencies and update some python packages under the
# assumption that this doesn't lower reproducibility significantly
# and because we require some recent additions in these packages

COPY requirements.txt install-requirements.sh /tmp/

RUN cd /tmp && \
    conda update --yes conda pip && \
    pip install --upgrade pip && \
    ./install-requirements.sh --requirements-file requirements.txt

# re-do font cache after update
RUN python -c "from matplotlib import font_manager"

# download all resources
COPY halfpipe/resource.py /tmp/
RUN cd /tmp && \
    python resource.py

# install halfpipe
COPY . /halfpipe/
RUN cd /halfpipe && \
    pip install . && \
    rm -rf ~/.cache/pip && \
    cd && \
    rm -rf /halfpipe/* /tmp/*

ENTRYPOINT ["/usr/local/miniconda/bin/halfpipe"]
