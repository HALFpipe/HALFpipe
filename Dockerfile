# syntax=docker/dockerfile:1.10

ARG fmriprep_version=25.0.0

# Stage 1: Base conda environment
FROM condaforge/miniforge3 AS conda
RUN conda config --system --append channels https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public && \
    conda config --system --set remote_max_retries 10 \
        --set remote_backoff_factor 2 \
        --set remote_connect_timeout_secs 60 \
        --set remote_read_timeout_secs 240

# Stage 2: Builder with conda-build and retry script
FROM conda AS builder
RUN conda install --yes "conda-build"

RUN cat <<EOF >"/usr/bin/retry"
#!/bin/bash
set -euo pipefail
attempt="1"
until "\$@"; do
    exit_code="\$?"
    if [ "\${attempt}" -ge "5" ]; then
        exit "\${exit_code}"
    fi
    sleep 10
    attempt=\$((attempt + 1))
done
EOF
RUN chmod "+x" "/usr/bin/retry"

FROM builder AS main_builder
WORKDIR /recipes

# We manually specify the numpy version for all conda build commands to silence
# an irrelevant warning as per https://github.com/conda/conda-build/issues/3170
ARG numpy_version=1.24

RUN --mount=source=recipes/rmath,target=/recipes/rmath \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "rmath" && conda index /opt/conda/conda-bld

RUN --mount=source=recipes/pytest-textual-snapshot,target=/recipes/pytest-textual-snapshot \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "pytest-textual-snapshot" && conda index /opt/conda/conda-bld

RUN --mount=source=recipes/afni,target=/recipes/afni \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "afni" && conda index /opt/conda/conda-bld

RUN --mount=source=recipes/migas,target=/recipes/migas \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "migas" && conda index /opt/conda/conda-bld

RUN --mount=source=recipes/nireports,target=/recipes/nireports \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "nireports" && conda index /opt/conda/conda-bld

# Tedana dependencies
RUN --mount=source=recipes/mapca,target=/recipes/mapca \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "mapca" && conda index /opt/conda/conda-bld
RUN --mount=source=recipes/pybtex-apa-style,target=/recipes/pybtex-apa-style \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "pybtex-apa-style" && conda index /opt/conda/conda-bld
RUN --mount=source=recipes/robustica,target=/recipes/robustica \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "robustica" && conda index /opt/conda/conda-bld
RUN --mount=source=recipes/tedana,target=/recipes/tedana \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "tedana" && conda index /opt/conda/conda-bld

# Niworkflows dependencies
RUN --mount=source=recipes/nitransforms,target=/recipes/nitransforms \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "nitransforms" && conda index /opt/conda/conda-bld
RUN --mount=source=recipes/niworkflows,target=/recipes/niworkflows \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "niworkflows" && conda index /opt/conda/conda-bld

# Subsequent builds can now find their dependencies from the local channel
RUN --mount=source=recipes/sdcflows,target=/recipes/sdcflows \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "sdcflows" && conda index /opt/conda/conda-bld

RUN --mount=source=recipes/smriprep,target=/recipes/smriprep \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "smriprep" && conda index /opt/conda/conda-bld

RUN --mount=source=recipes/fmriprep,target=/recipes/fmriprep \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "fmriprep" && conda index /opt/conda/conda-bld

RUN --mount=source=recipes/fmripost_aroma,target=/recipes/fmripost_aroma \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "fmripost_aroma" && conda index /opt/conda/conda-bld

# Mount .git folder too for setuptools_scm
RUN --mount=source=recipes/halfpipe,target=/recipes/halfpipe/recipes/halfpipe \
    --mount=source=src,target=/recipes/halfpipe/src \
    --mount=source=pyproject.toml,target=/recipes/halfpipe/pyproject.toml \
    --mount=source=.git,target=/recipes/halfpipe/.git \
    --mount=type=cache,target=/opt/conda/pkgs \
    retry conda build --no-anaconda-upload --numpy "${numpy_version}" "halfpipe/recipes/halfpipe" && conda index /opt/conda/conda-bld


FROM conda AS install
COPY --from=main_builder /opt/conda/conda-bld/ /opt/conda/conda-bld/

RUN --mount=type=cache,target=/opt/conda/pkgs \
    conda create --name "fmriprep" --yes --use-local \
    -c https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public \
    python=3.11 nodejs sqlite halfpipe

RUN conda clean --yes --all --force-pkgs-dirs && \
    find /opt/conda -follow -type f -name "*.a" -delete && \
    rm -rf /opt/conda/conda-bld

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
    PATH="/opt/conda/bin:$PATH"
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
