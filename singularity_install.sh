#!/bin/bash

##

SINGULARITY_VERSION=2.4.5

##

function runCmd() {
	cmd="$*"
	echo $cmd
	$cmd
}

TMP=$(mktemp -d)

runCmd wget https://github.com/singularityware/singularity/releases/download/${SINGULARITY_VERSION}/singularity-${SINGULARITY_VERSION}.tar.gz -P ${TMP}

runCmd tar xf ${TMP}/singularity-${SINGULARITY_VERSION}.tar.gz -C ${TMP}

WD=$(pwd)
mkdir -p ${WD}/singularity

cd ${TMP}/singularity-${SINGULARITY_VERSION}

runCmd ./configure --prefix=${WD}/singularity

runCmd make

runCmd make install

cd ${WD}

export PYTHONPATH=""
export PATH=$(pwd)/singularity/bin:${PATH}

mkdir -p cache
export SINGULARITY_CACHEDIR=$(pwd)/cache

runCmd singularity build pipeline docker://mindandbrain/pipeline:dev
 
 
