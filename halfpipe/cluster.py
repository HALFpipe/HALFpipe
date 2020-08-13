# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path

import logging

from .utils import first
from .io import make_cachefilepath

script_template = """#!/bin/bash
#SBATCH --job-name=halfpipe
#SBATCH --output=batch.log.txt

#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=5888M

#SBATCH --partition=medium

#SBATCH --array=1-{n_chunks}

singularity run \
--no-home \
--cleanenv \
--bind /:/ext \
{singularity_container} \
--workdir {cwd} \
--only-run \
--execgraph-file {execgraph_file} \
--only-chunk-index ${{SLURM_ARRAY_TASK_ID}} \
--nipype-n-procs 2 \
--verbose

"""


def create_example_script(workdir, execgraphs):
    uuid = first(execgraphs).uuid
    n_chunks = len(execgraphs) - 1  # omit model chunk
    assert n_chunks > 1
    execgraph_file = make_cachefilepath(f"execgraph.{n_chunks:02d}_chunks", uuid)
    data = {
        "n_chunks": n_chunks + 1,  # one-based indexing
        "singularity_container": os.environ["SINGULARITY_CONTAINER"],
        "cwd": str(Path(workdir).resolve()),
        "execgraph_file": str(Path(workdir).resolve() / execgraph_file)
    }
    st = script_template.format(**data)
    stpath = "submit.slurm.sh"
    logging.getLogger("halfpipe").log(25, f'A submission script template was created at "{stpath}"')
    with open(Path(workdir) / stpath, "w") as f:
        f.write(st)
