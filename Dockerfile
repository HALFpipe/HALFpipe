# syntax=docker/dockerfile-upstream:master

ARG FMRIPREP_VERSION=20.2.7

# Build all custom recipes in one command. We build our own conda packages to simplify
# the environment creation process, as some of them were only available in pypi
FROM condaforge/mambaforge:latest AS builder

RUN mamba update --yes --all
RUN mamba install --yes "boa" "conda-verify"
COPY recipes /recipes

# We manually specify the numpy version here to silence an irrelevant warning as per
# https://github.com/conda/conda-build/issues/3170
RUN for pkg in rmath traits nipype niflow-nipype1-workflows sqlalchemy pybids nitransforms tedana templateflow niworkflows sdcflows smriprep fmriprep halfpipe; do \
        conda mambabuild --numpy "1.24" --no-anaconda-upload --use-local /recipes/${FMRIPREP_VERSION}/$pkg  && \
        conda build purge; \
    done

# We install built recipes and cleans unnecessary files such as static libraries
FROM condaforge/mambaforge:latest AS install

COPY --from=builder /opt/conda/conda-bld/ /opt/conda/conda-bld/
RUN mamba install --yes --use-local \
    "python=3.11" "nodejs" "halfpipe" && \
    mamba clean --yes --all --force-pkgs-dirs \
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
FROM nipreps/fmriprep:${FMRIPREP_VERSION}

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
ENV PATH="${PATH//:\/usr\/lib\/ants/}"

# Add `coinstac` server components
COPY --from=coinstacteam/coinstac-base:latest /server/ /server/

# Add git config for datalad commands
RUN git config --global user.name "Halfpipe" \
    && git config --global user.email "halfpipe@fmri.science"

# Copy `conda` from `install` stage
COPY --from=install /opt/conda/ /opt/conda/

# The fmriprep container comes with conda in `/usr/local/miniconda`.
# Instead, halfpipe uses conda from the corresponding docker image,
# where it is installed in `/opt/conda`.
# Therefore, we update the `PATH` to reflect new conda location
ENV PATH="${PATH/\/usr\/local\/miniconda\/bin//opt/conda/bin}" \
    MAMBA_EXE="/opt/conda/bin/mamba"

# Download all resources
RUN --mount=source=src/halfpipe/resource.py,target=/resource.py \
    python /resource.py

ENTRYPOINT ["/opt/conda/bin/halfpipe"]
