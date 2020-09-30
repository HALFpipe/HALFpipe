# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path
from math import ceil

import logging

from .utils import first
from .io import make_cachefilepath

script_template = """#!/bin/bash
#SBATCH --job-name=halfpipe
#SBATCH --output=halfpipe.log.txt

#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={n_cpus}
#SBATCH --mem-per-cpu={mem_per_cpu}

#SBATCH --array=1-{n_chunks}

singularity run \\
--no-home \\
--cleanenv \\
--bind /:/ext \\
{singularity_container} \\
--workdir {cwd} \\
--only-run \\
--execgraph-file {execgraph_file} \\
--only-chunk-index ${{SLURM_ARRAY_TASK_ID}} \\
--nipype-n-procs 2 \\
--verbose

"""


def create_example_script(workdir, execgraphs):
    uuid = first(execgraphs).uuid
    n_chunks = len(execgraphs) - 1  # omit model chunk
    assert n_chunks > 1
    execgraph_file = make_cachefilepath(f"execgraph.{n_chunks:d}_chunks", uuid)

    n_cpus = 2
    mem_gb = max(node.mem_gb for execgraph in execgraphs for node in execgraph.nodes)
    mem_per_cpu = f"{ceil(mem_gb / n_cpus * 1536):d}M"  # fudge factor

    data = {
        "n_chunks": n_chunks,  # one-based indexing
        "singularity_container": os.environ["SINGULARITY_CONTAINER"],
        "cwd": str(Path(workdir).resolve()),
        "execgraph_file": str(Path(workdir).resolve() / execgraph_file),
        "n_cpus": n_cpus,
        "mem_per_cpu": mem_per_cpu,
    }
    st = script_template.format(**data)
    stpath = "submit.slurm.sh"
    logging.getLogger("halfpipe").log(25, f'A submission script template was created at "{stpath}"')
    with open(Path(workdir) / stpath, "w") as f:
        f.write(st)
