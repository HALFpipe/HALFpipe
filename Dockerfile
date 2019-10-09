ARG FMRIPREP_VERSION=1.1.6
ARG MRIQC_VERSION=0.14.2
ARG CPAC_VERSION=v1.3.0

FROM poldracklab/fmriprep:${FMRIPREP_VERSION}

#ENV HTTP_PROXY http://141.42.1.215:8080
#ENV HTTPS_PROXY https://141.42.1.215:8080

ARG MRIQC_VERSION

RUN mkdir -p /root/src/mriqc && \
    curl -sSL "https://api.github.com/repos/poldracklab/mriqc/tarball/${MRIQC_VERSION}" \
    | tar -xzC /root/src/mriqc --strip-components 1 && \
    cd /root/src/mriqc && \
    pip install -r requirements.txt && \
    pip install .[all] && \
    rm -rf ~/.cache/pip

 RUN apt-get update && \
     apt-get install -y graphviz \
       graphviz-dev

# RUN mkdir -p /root/src/cpac && \
#     curl -sSL "https://api.github.com/repos/FCP-INDI/C-PAC/tarball/${CPAC_VERSION}" \
#     | tar -xzC /root/src/cpac --strip-components 1 && \
#     2to3 --no-diffs --verbose -w -n /root/src/cpac/*.py && \
#     cd /root/src/cpac && \
#     pip install -r requirements.txt && \
#     pip install .[all] --no-compile && \
#     rm -rf ~/.cache/pip

RUN mkdir /ext

COPY ./qualitycheck /root/src/qualitycheck
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash && \
  apt-get install -y nodejs &&  \
  cd /root/src/qualitycheck && \
  npm install && npm run build && \
  cp -r dist/index.html /root/src && \
  cd .. && rm -rf qualitycheck && \
  apt-get purge -y nodejs

COPY . /root/src/pipeline
RUN cd /root/src/pipeline && \
    cp ../index.html pipeline && \
    python setup.py install && \
    rm -rf ~/.cache/pip && \
    mv /root/src/pipeline/static /opt/static

ENTRYPOINT ["/usr/local/miniconda/bin/pipeline"]
