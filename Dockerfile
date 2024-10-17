# syntax=docker/dockerfile-upstream:master

ARG fmriprep_version=20.2.7

# Build all custom recipes in one command. We build our own conda packages to simplify
# the environment creation process, as some of them are not available on conda-forge
FROM condaforge/miniforge3:latest AS builder

RUN conda config --system --set remote_max_retries 8 \
    --set remote_backoff_factor 2 \
    --set remote_connect_timeout_secs 60 \
    --set remote_read_timeout_secs 240
RUN conda install --yes "conda-build"

# We manually specify the numpy version for all conda build commands to silence
# an irrelevant warning as per https://github.com/conda/conda-build/issues/3170

FROM builder AS rmath
RUN --mount=source=recipes/rmath,target=/rmath \
    conda build --no-anaconda-upload --numpy "1.24" "rmath"

FROM builder AS pytest-textual-snapshot
RUN --mount=source=recipes/pytest-textual-snapshot,target=/pytest-textual-snapshot \
    conda build --no-anaconda-upload --numpy "1.24" "pytest-textual-snapshot"

FROM builder AS nipype
RUN --mount=source=recipes/traits,target=/traits \
    conda build --no-anaconda-upload --numpy "1.24" "traits"
RUN --mount=source=recipes/nipype,target=/nipype \
    conda build --no-anaconda-upload --numpy "1.24" "nipype"
RUN --mount=source=recipes/niflow-nipype1-workflows,target=/niflow-nipype1-workflows \
    conda build --no-anaconda-upload --numpy "1.24" "niflow-nipype1-workflows"

FROM builder AS nitransforms
ARG fmriprep_version
RUN --mount=source=recipes/${fmriprep_version}/nitransforms,target=/nitransforms \
    conda build --no-anaconda-upload --numpy "1.24" "nitransforms"

FROM builder AS tedana
ARG fmriprep_version
RUN --mount=source=recipes/${fmriprep_version}/tedana,target=/tedana \
    conda build --no-anaconda-upload --numpy "1.24" "tedana"

FROM builder AS templateflow
ARG fmriprep_version
RUN --mount=source=recipes/${fmriprep_version}/templateflow,target=/templateflow \
    conda build --no-anaconda-upload --numpy "1.24" "templateflow"

FROM builder AS niworkflows
ARG fmriprep_version
COPY --from=nitransforms /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=nipype /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=templateflow /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/${fmriprep_version}/niworkflows,target=/niworkflows \
    conda build --no-anaconda-upload --numpy "1.24" "niworkflows"

FROM builder AS sdcflows
ARG fmriprep_version
COPY --from=nipype /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=niworkflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=templateflow /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/${fmriprep_version}/sdcflows,target=/sdcflows \
    conda build --no-anaconda-upload --numpy "1.24" "sdcflows"

FROM builder AS smriprep
ARG fmriprep_version
COPY --from=nipype /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=niworkflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=templateflow /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/${fmriprep_version}/smriprep,target=/smriprep \
    conda build --no-anaconda-upload --numpy "1.24" "smriprep"

FROM builder AS fmriprep
ARG fmriprep_version
COPY --from=nipype /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=niworkflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=sdcflows /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=smriprep /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=tedana /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
RUN --mount=source=recipes/${fmriprep_version}/fmriprep,target=/fmriprep \
    conda build --no-anaconda-upload --numpy "1.24" "fmriprep"

FROM builder AS halfpipe
COPY --from=fmriprep /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=rmath /opt/conda/conda-bld /opt/conda/conda-bld
COPY --from=pytest-textual-snapshot /opt/conda/conda-bld /opt/conda/conda-bld
RUN conda index /opt/conda/conda-bld
# Mount .git folder too for setuptools_scm
RUN --mount=source=recipes/halfpipe,target=/halfpipe/recipes/halfpipe \
    --mount=source=src,target=/halfpipe/src \
    --mount=source=pyproject.toml,target=/halfpipe/pyproject.toml \
    --mount=source=.git,target=/halfpipe/.git \
    conda build --no-anaconda-upload --numpy "1.24" "halfpipe/recipes/halfpipe"

# We install built recipes and cleans unnecessary files such as static libraries
FROM condaforge/miniforge3:latest AS install

COPY --from=halfpipe /opt/conda/conda-bld/ /opt/conda/conda-bld/
RUN conda install --yes --use-local \
    "python=3.11" "nodejs" "halfpipe" "sqlite" && \
    conda clean --yes --all --force-pkgs-dirs \
    && find /opt/conda -follow -type f -name "*.a" -delete \
    && rm -rf /opt/conda/conda-bld

# Re-apply `matplotlib` settings after re-installing conda. This silences
# a warning that will otherwise be printed every time `matplotlib` is imported.
# This command re-caches fonts and sets 'Agg' as default backend for `matplotlib`.
# Taken from fmriprep's Dockerfile
RUN python -c "from matplotlib import font_manager" && \
    sed -i '/backend:/s/^#*//;/^backend/s/: .*/: Agg/' \
    $( python -c "import matplotlib; print(matplotlib.matplotlib_fname())" )

# Create the final image based on existing fmriprep image
FROM nipreps/fmriprep:${fmriprep_version}

# Create these empty directories, so that they can be used for singularity
# bind mounts later
RUN mkdir /ext /host \
    && chmod a+rwx /ext /host

# Use `/var/cache` for downloaded resources instead of `/home/fmriprep/.cache`,
# because it is less likely to be obscured by default bind mounts when running with
# singularity. These have been reported by users running on specific HPC systems
ENV XDG_CACHE_HOME="/var/cache" \
    HALFPIPE_RESOURCE_DIR="/var/cache/halfpipe" \
    TEMPLATEFLOW_HOME="/var/cache/templateflow"
RUN mv /home/fmriprep/.cache/templateflow /var/cache

# We install ants previously using conda (through a dependency in the halfpipe
# recipe), to get an important bug fix (#691). We delete the ants that came with
# fmriprep and update the `PATH` to reflect the new ants location
RUN rm -rf /usr/lib/ants
ENV PATH="${PATH//\/usr\/lib\/ants/}"

# Add `coinstac` server components
COPY --from=coinstacteam/coinstac-base:latest /server/ /server/

# Add git config for datalad commands
RUN git config --global user.name "HALFpipe" \
    && git config --global user.email "halfpipe@fmri.science"

# Copy `conda` from `install` stage
COPY --from=install /opt/conda/ /opt/conda/

# The `fmriprep` container comes with conda in `/usr/local/miniconda`.
# Instead, halfpipe uses conda from the corresponding docker image,
# where it is installed in `/opt/conda`.
# Therefore, we update the `PATH` to reflect new conda location
ENV PATH="${PATH/\/usr\/local\/miniconda\/bin//opt/conda/bin}" \
    MAMBA_EXE="/opt/conda/bin/mamba"

# Download all resources
RUN --mount=source=src/halfpipe/resource.py,target=/resource.py \
    python /resource.py

ENTRYPOINT ["/opt/conda/bin/halfpipe"]
