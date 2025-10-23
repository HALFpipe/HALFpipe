# syntax=docker/dockerfile:1.10

ARG fmriprep_version=25.1.1

FROM condaforge/miniforge3 AS install
RUN conda config --system --append channels https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public && \
    conda config --system --set remote_max_retries 10 \
        --set remote_backoff_factor 2 \
        --set remote_connect_timeout_secs 60 \
        --set remote_read_timeout_secs 240

RUN --mount=type=cache,target=/opt/conda/pkgs \
    --mount=source=conda-bld,target=/conda-bld \
    conda create --yes \
    --name "fmriprep" \
    --channel file:///conda-bld \
    --channel https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public \
    python=3.12 nodejs sqlite halfpipe

RUN conda clean --yes --all --force-pkgs-dirs && \
    find /opt/conda -follow -type f -name "*.a" -delete

RUN conda run --name="fmriprep" python -c "from matplotlib import font_manager" && \
    sed -i '/backend:/s/^#*//;/^backend/s/: .*/: Agg/' \
        $(conda run --name="fmriprep" python -c "import matplotlib; print(matplotlib.matplotlib_fname())")

RUN echo "6.0.0" >/opt/conda/envs/fmriprep/etc/fslversion

FROM nipreps/fmriprep:${fmriprep_version}

# Create these empty directories, so that they can be used for singularity
# bind mounts later
RUN mkdir /ext /host && \
    chmod a+rwx /ext /host

ENV XDG_CACHE_HOME="/var/cache" \
    HALFPIPE_RESOURCE_DIR="/var/cache/halfpipe" \
    TEMPLATEFLOW_HOME="/var/cache/templateflow" \
    PATH="/opt/conda/bin:$PATH" \
    MATLABROOT="/opt/conda/envs/fmriprep/lib/mcr"
ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$MATLABROOT/bin/glnxa64:$MATLABROOT/runtime/glnxa64:$MATLABROOT/sys/os/glnxa64:$MATLABROOT/sys/java/jre/glnxa64/jre/lib/amd64/native_threads:$MATLABROOT/sys/java/jre/glnxa64/jre/lib/amd64/server:$MATLABROOT/sys/java/jre/glnxa64/jre/lib/amd64"
RUN mv /home/fmriprep/.cache/templateflow /var/cache

# Add `coinstac` server components
COPY --from=coinstacteam/coinstac-base:latest /server/ /server/

# Add git config for datalad commands
RUN git config --global user.name "HALFpipe" && \
    git config --global user.email "halfpipe@fmri.science"

RUN rm -rf /opt/conda
COPY --from=install /opt/conda/ /opt/conda/

# Download all resources
RUN --mount=source=src/halfpipe/resource.py,target=/resource.py \
    conda run --name="fmriprep" python /resource.py

ENTRYPOINT ["/opt/conda/envs/fmriprep/bin/halfpipe"]
