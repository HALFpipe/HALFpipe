#!/bin/bash

function runCmd() {
	cmd="$*"
	echo $cmd
	$cmd
}

export PYTHONPATH=""
export PATH=$(pwd)/singularity/bin:${PATH}

runCmd singularity run -B /:/ext pipeline