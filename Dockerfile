FROM nipreps/fmriprep:20.2.7

RUN mkdir /ext /host \
 && chmod a+rwx /ext /host

ENV PATH="/usr/local/miniconda/bin:$PATH"

# Use `/var/cache` for downloaded resources instead of
# `/home/fmriprep/.cache`, because it is less likely to be
# obscured by default container bind mounts when running
# with Singularity
ENV XDG_CACHE_HOME="/var/cache" \
    HALFPIPE_RESOURCE_DIR="/var/cache/halfpipe" \
    TEMPLATEFLOW_HOME="/var/cache/templateflow"
RUN mv /home/fmriprep/.cache/templateflow /var/cache

# Re-install `conda` and dependency `python` packages
COPY requirements.txt install-requirements.sh /tmp/
RUN rm -rf /usr/local/miniconda \
 && cd /tmp \
 && curl --show-error --location \
        "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh" \
        --output "miniconda.sh" \
 && bash miniconda.sh -b -p /usr/local/miniconda \
 && mamba install --yes "python=3.11" "nomkl" "pip" "gdb" "nodejs" \
 && ./install-requirements.sh --requirements-file requirements.txt \
 && cd \
 && sync \
 && mamba clean --yes --all --force-pkgs-dirs \
 && sync \
 && find /usr/local/miniconda/ -follow -type f -name "*.a" -delete \
 && rm -rf ~/.conda \
        /var/cache/apt /var/lib/apt \
        ~/.cache/pip /var/cache/pip \
        /tmp/* /var/tmp/* \
 && sync

# Re-apply matplotlib settings after updating
# Taken from `fmriprep`
# Pre-caches fonts, set 'Agg' as default backend for matplotlib
RUN python -c "from matplotlib import font_manager" \
 && sed -i '/backend:/s/^#*//;/^backend/s/: .*/: Agg/' \
        $( python -c "import matplotlib; print(matplotlib.matplotlib_fname())" )

# Download all resources
COPY halfpipe/resource.py /tmp/
RUN python /tmp/resource.py \
 && sync \
 && rm -rf /tmp/* \
 && sync

# Add coinstac server components
COPY --from=coinstacteam/coinstac-base:latest /server/ /server/

# Install HALFpipe
COPY . /halfpipe/
RUN cd /halfpipe \
 && /usr/local/miniconda/bin/python -m pip install --no-deps --no-cache-dir . \
 && cd \
 && rm -rf /halfpipe \
        ~/.cache/pip /var/cache/pip \
        /tmp/* /var/tmp/* \
 && sync

ENTRYPOINT ["/usr/local/miniconda/bin/halfpipe"]
