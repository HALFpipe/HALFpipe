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
    ./install-requirements.sh --requirements-file requirements.txt && sync && \
    conda clean --yes --all --force-pkgs-dirs && sync && \
    find /usr/local/miniconda/ -follow -type f -name "*.a" -delete && sync

# re-do matplotlib settings after installing requirements
# these are taken from fmriprep
# precaching fonts, set 'Agg' as default backend for matplotlib
RUN python -c "from matplotlib import font_manager" && \
    sed -i '/backend:/s/^#*//;/^backend/s/: .*/: Agg/' \
    $( python -c "import matplotlib; print(matplotlib.matplotlib_fname())" )

# download all resources
COPY halfpipe/resource.py /tmp/
RUN python /tmp/resource.py

# install halfpipe
COPY . /halfpipe/
RUN cd /halfpipe && \
    pip install --no-deps --use-feature=in-tree-build . && \
    rm -rf ~/.cache/pip && \
    cd && \
    rm -rf /halfpipe /tmp/*

ENTRYPOINT ["/usr/local/miniconda/bin/halfpipe"]
