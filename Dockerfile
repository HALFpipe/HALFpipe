ARG FMRIPREP_VERSION=20.2.1
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
RUN conda update --yes conda && \
    conda install --yes \
    "cffi>=1.12" \
    "numpy>=1.20" \
    "mkl>=2021" \
    "mkl_fft>=1.3.0" \
    "scipy>=1.6" \
    "pandas>=1.2.4" \
    "matplotlib>=3.3" \
    "statsmodels>=0.12.2" \
    "scikit-learn>=0.24.0" \
    "openpyxl" \
    "mpmath>=1.1.0" \
    "inflect" \
    "inflection" \
    "seaborn" \
    "tabulate" \
    "chardet>=4.0" \
    "line_profiler" \
    "more-itertools"

COPY requirements.txt /halfpipe/

# re-do font cache after update
RUN python -c "from matplotlib import font_manager"

# force install of patsy dev version, as it contains an important fix
RUN pip install git+https://github.com/pydata/patsy.git

# install dependencies and force reinstall of nipreps and nipype
RUN cd /halfpipe && \
    pip uninstall --yes fmriprep smriprep niworkflows nipype && \
    pip install -r requirements.txt

# download all resources
COPY halfpipe/resource.py /halfpipe/
RUN cd /halfpipe && \
    python resource.py

# install halfpipe
COPY . /halfpipe/
RUN cd /halfpipe && \
    pip install . && \
    rm -rf ~/.cache/pip && \
    cd .. && \
    rm -rf /halfpipe/*
    
ENTRYPOINT ["/usr/local/miniconda/bin/halfpipe"]
