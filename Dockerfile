# syntax=docker/dockerfile:1.10

ARG fmriprep_version=25.0.0
# We manually specify the numpy version for all conda build commands to silence
# an irrelevant warning as per https://github.com/conda/conda-build/issues/3170

# Stage 1: Base conda environment
FROM condaforge/miniforge3 AS conda
RUN conda config --system --append channels https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public && \
    conda config --system --set remote_max_retries 10 \
        --set remote_backoff_factor 2 \
        --set remote_connect_timeout_secs 60 \
        --set remote_read_timeout_secs 240

# Stage 2: Builder with conda-build and retry script
FROM conda AS builder
RUN conda install --yes "conda-build" boto3 loguru

RUN apt-get update && \
    apt-get install git-lfs curl unzip -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

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

COPY build_halfpipe_deps.py /tmp/build_halfpipe_deps.py

ARG numpy_version=1.24
RUN echo ${numpy_version}

RUN --mount=type=secret,id=AWS_ACCESS_KEY_ID,env=AWS_ACCESS_KEY_ID \
    --mount=type=secret,id=AWS_SECRET_ACCESS_KEY,env=AWS_SECRET_ACCESS_KEY\
    --mount=type=secret,id=AWS_ENDPOINT_URL,env=AWS_ENDPOINT_URL \
    --mount=type=secret,id=CONDA_BUCKET,env=CONDA_BUCKET \
    --mount=source=recipes,target=/recipes \
    retry python /tmp/build_halfpipe_deps.py /recipes --build --verbose && conda index /opt/conda/conda-bld

RUN --mount=source=src,target=/recipes/halfpipe/src \
    --mount=source=recipes/halfpipe,target=/recipes/halfpipe/recipes/halfpipe \
    --mount=type=bind,source=recipes/conda_build_config.yaml,target=/recipes/conda_build_config.yaml \
    --mount=source=pyproject.toml,target=/recipes/halfpipe/pyproject.toml \
    --mount=source=.git,target=/recipes/halfpipe/.git \
    retry conda build "halfpipe/recipes/halfpipe" --no-anaconda-upload --numpy "${numpy_version}" && conda index /opt/conda/conda-bld

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
