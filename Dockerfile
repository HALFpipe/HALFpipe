# syntax=docker/dockerfile:1.10

ARG fmriprep_version=25.0.0

FROM condaforge/miniforge3 AS conda
RUN conda config --system --append channels https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public && \
    conda config --system --set remote_max_retries 10 \
        --set remote_backoff_factor 2 \
        --set remote_connect_timeout_secs 60 \
        --set remote_read_timeout_secs 240

# Build all custom recipes in one command. We build our own conda packages to simplify
# the environment creation process, as some of them are not available on conda-forge
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

# We manually specify the numpy version for all conda build commands to silence
# an irrelevant warning as per https://github.com/conda/conda-build/issues/3170

FROM builder AS rmath
RUN --mount=source=recipes/rmath,target=/rmath \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "rmath"

FROM builder AS pytest-textual-snapshot
RUN --mount=source=recipes/pytest-textual-snapshot,target=/pytest-textual-snapshot \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "pytest-textual-snapshot"

FROM builder AS afni
RUN --mount=source=recipes/afni,target=/afni \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "afni"

FROM builder AS mapca
RUN --mount=source=recipes/mapca,target=/mapca \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "mapca"

FROM builder AS migas
RUN --mount=source=recipes/migas,target=/migas \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "migas"

FROM builder AS nireports
RUN --mount=source=recipes/nireports,target=/nireports \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "nireports"

FROM builder AS nitransforms
RUN --mount=source=recipes/nitransforms,target=/nitransforms \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "nitransforms"

FROM builder AS tedana
COPY --from=mapca /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/tedana,target=/tedana \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "tedana"

FROM builder AS niworkflows
COPY --from=nitransforms /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/niworkflows,target=/niworkflows \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/src_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "niworkflows"

FROM builder AS sdcflows
COPY --from=niworkflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=migas /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/sdcflows,target=/sdcflows \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "sdcflows"

FROM builder AS smriprep
COPY --from=niworkflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=migas /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/smriprep,target=/smriprep \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "smriprep"

FROM builder AS fmriprep
COPY --from=niworkflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=sdcflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=smriprep /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=tedana /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=nireports /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/fmriprep,target=/fmriprep \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "fmriprep"

FROM builder AS fmripost_aroma
COPY --from=niworkflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=nitransforms /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=sdcflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=smriprep /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=nireports /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=fmriprep /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/fmripost_aroma,target=/fmripost_aroma \
    --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/opt/conda/conda-bld/git_cache \
    retry conda build --no-anaconda-upload --numpy "1.24" "fmripost_aroma"

FROM builder AS halfpipe
COPY --from=fmriprep /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=rmath /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=pytest-textual-snapshot /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=afni /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=fmripost_aroma /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
# Mount .git folder too for setuptools_scm
RUN --mount=source=recipes/halfpipe,target=/halfpipe/recipes/halfpipe \
    --mount=source=src,target=/halfpipe/src \
    --mount=source=pyproject.toml,target=/halfpipe/pyproject.toml \
    --mount=source=.git,target=/halfpipe/.git \
    --mount=type=cache,target=/opt/conda/pkgs \
    retry conda build --no-anaconda-upload --numpy "1.24" "halfpipe/recipes/halfpipe"

# We install built recipes and clean unnecessary files such as static libraries
FROM conda AS install
RUN conda config --system --append channels https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public
COPY --from=halfpipe /opt/conda/conda-bld/ /opt/conda/conda-bld/
RUN --mount=type=cache,target=/opt/conda/pkgs \
    conda create --name "fmriprep" --yes --use-local \
    "python=3.11" "nodejs" "sqlite" "halfpipe"

RUN conda clean --yes --all --force-pkgs-dirs && \
    find /opt/conda -follow -type f -name "*.a" -delete && \
    rm -rf /opt/conda/conda-bld

# Re-apply `matplotlib` settings after re-installing conda. This silences
# a warning that will otherwise be printed every time `matplotlib` is imported.
# This command re-caches fonts and sets 'Agg' as default backend for `matplotlib`.
# Taken from fmriprep's Dockerfile
RUN conda run --name="fmriprep" python -c "from matplotlib import font_manager" && \
    sed -i '/backend:/s/^#*//;/^backend/s/: .*/: Agg/' \
        $(conda run --name="fmriprep" python -c "import matplotlib; print(matplotlib.matplotlib_fname())")

RUN echo "6.0.0" > /opt/conda/envs/fmriprep/etc/fslversion

# Create the final image based on existing fmriprep image
FROM nipreps/fmriprep:${fmriprep_version}

# Create these empty directories, so that they can be used for singularity
# bind mounts later
RUN mkdir /ext /host && \
    chmod a+rwx /ext /host

# Use `/var/cache` for downloaded resources instead of `/home/fmriprep/.cache`,
# because it is less likely to be obscured by default bind mounts when running with
# singularity. These have been reported by users running on specific HPC systems
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

# Copy `conda` from `install` stage
RUN rm -rf /opt/conda
COPY --from=install /opt/conda/ /opt/conda/

# Download all resources
RUN --mount=source=src/halfpipe/resource.py,target=/resource.py \
    conda run --name="fmriprep" python /resource.py

ENTRYPOINT ["/opt/conda/envs/fmriprep/bin/halfpipe"]
