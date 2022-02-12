FROM nipreps/fmriprep:20.2.7

ENV PATH="/usr/local/miniconda/bin:$PATH" \
    XDG_CACHE_HOME="/home/fmriprep/.cache"

ENV HALFPIPE_RESOURCE_DIR="${XDG_CACHE_HOME}/halfpipe" \
    TEMPLATEFLOW_HOME="${XDG_CACHE_HOME}/templateflow"

RUN mkdir /ext /halfpipe && \
    chmod a+rwx /ext /halfpipe

# Re-install `conda` and dependency `python` packages

COPY requirements.txt install-requirements.sh /tmp/

RUN rm -rf /usr/local/miniconda && \
    cd /tmp && \
    curl --show-error --location \
        "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" \
        --output "miniconda.sh" &&  \
    bash miniconda.sh -b -p /usr/local/miniconda && \
    ./install-requirements.sh --requirements-file requirements.txt && \
    sync && \
    conda clean --yes --all --force-pkgs-dirs && \
    sync && \
    find /usr/local/miniconda/ -follow -type f -name "*.a" -delete && \
    rm -rf /tmp/* && \
    sync

# Re-apply matplotlib settings after updating
# Taken from `fmriprep`
# Pre-caches fonts, set 'Agg' as default backend for matplotlib
RUN python -c "from matplotlib import font_manager" && \
    sed -i '/backend:/s/^#*//;/^backend/s/: .*/: Agg/' \
    $( python -c "import matplotlib; print(matplotlib.matplotlib_fname())" )

# Download all resources
COPY halfpipe/resource.py /tmp/
RUN python /tmp/resource.py

# Install halfpipe
COPY . /halfpipe/
RUN cd /halfpipe && \
    /usr/local/miniconda/bin/python -m pip install --no-deps --no-cache-dir . && \
    rm -rf ~/.cache/pip ~/.conda && \
    cd && \
    rm -rf /halfpipe/* /tmp/*

ENTRYPOINT ["/usr/local/miniconda/bin/halfpipe"]
