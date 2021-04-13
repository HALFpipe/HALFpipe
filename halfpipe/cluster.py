# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path
from math import ceil

import logging

from .io import make_cachefilepath

script_templates = dict(
    slurm="""#!/bin/bash
#
#
#SBATCH --job-name=halfpipe
#SBATCH --output=halfpipe.log.txt
#
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={n_cpus}
#SBATCH --mem-per-cpu={mem_mb}M
#
#SBATCH --array=1-{n_chunks}

if ! [ -x "$(command -v singularity)" ]; then
module load singularity
fi

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

""",
    torque="""#!/bin/bash
#
#
#PBS -N halfpipe
#PBS -j oe
#PBS -o halfpipe.log.txt
#$ -cwd
#
#PBS -l nodes=1:ppn=2
#PBS -l walltime=24:00:00
#PBS -l mem={mem_mb}mb
#
#PBS -J 1-{n_chunks}

if ! [ -x "$(command -v singularity)" ]; then
module load singularity
fi

singularity run \\
--no-home \\
--cleanenv \\
--bind /:/ext \\
{singularity_container} \\
--workdir {cwd} \\
--only-run \\
--execgraph-file {execgraph_file} \\
--only-chunk-index ${{PBS_ARRAY_INDEX}} \\
--nipype-n-procs 2 \\
--verbose


""",
    sge="""#!/bin/bash
#
#
#$ -N halfpipe
#$ -j y
#$ -o halfpipe.log.txt
#$ -cwd
#
#$ -pe smp 2
#$ -l h_rt=24:0:0
#$ -l mem={mem_mb}M
#
#$ -t 1-{n_chunks}

if ! [ -x "$(command -v singularity)" ]; then
module load singularity
fi

singularity run \\
--no-home \\
--cleanenv \\
--bind /:/ext \\
{singularity_container} \\
--workdir {cwd} \\
--only-run \\
--execgraph-file {execgraph_file} \\
--only-chunk-index ${{SGE_TASK_ID}} \\
--nipype-n-procs 2 \\
--verbose

""",
)


def create_example_script(workdir, execgraphs):
    uuid = execgraphs[0].uuid
    n_chunks = len(execgraphs) - 1  # omit model chunk
    assert n_chunks > 1
    execgraph_file = make_cachefilepath(f"execgraph.{n_chunks:d}_chunks", uuid)

    n_cpus = 2
    nipype_max_mem_gb = max(node.mem_gb for execgraph in execgraphs for node in execgraph.nodes)
    mem_mb = f"{ceil(nipype_max_mem_gb / n_cpus * 1536):d}"  # fudge factor

    data = {
        "n_chunks": n_chunks,  # one-based indexing
        "singularity_container": os.environ["SINGULARITY_CONTAINER"],
        "cwd": str(Path(workdir).resolve()),
        "execgraph_file": str(Path(workdir).resolve() / execgraph_file),
        "n_cpus": n_cpus,
        "mem_mb": mem_mb,
    }

    for cluster_type, script_template in script_templates.items():
        st = script_template.format(**data)
        stpath = f"submit.{cluster_type}.sh"
        logging.getLogger("halfpipe").log(25, f'A submission script template was created at "{stpath}"')
        with open(Path(workdir) / stpath, "w") as f:
            f.write(st)
