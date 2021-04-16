# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path
from math import ceil
from typing import OrderedDict

from .io import make_cachefilepath
from .utils import logger, inflect_engine as p

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
#SBATCH --mem-per-cpu={mem_mb:d}M
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
--graphs-file {graphs_file} \\
--subject-chunks \\
--only-chunk-index ${{SLURM_ARRAY_TASK_ID}} \\
--nipype-n-procs 2 \\
--verbose {extra_args}

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
#PBS -l mem={mem_mb:d}mb
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
--graphs-file {graphs_file} \\
--subject-chunks \\
--only-chunk-index ${{PBS_ARRAY_INDEX}} \\
--nipype-n-procs 2 \\
--verbose {extra_args}


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
#$ -l mem={mem_mb:d}M
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
--graphs-file {graphs_file} \\
--subject-chunks \\
--only-chunk-index ${{SGE_TASK_ID}} \\
--nipype-n-procs 2 \\
--nipype-memory-gb {mem_gb} {extra_args}

""",
)


def create_example_script(workdir, graphs: OrderedDict, opts):
    uuid = next(iter(graphs)).uuid
    n_chunks = len(graphs) - 1  # omit model chunk
    assert n_chunks > 1
    graphs_file = make_cachefilepath(f"graphs.{n_chunks:d}_chunks", uuid)

    n_cpus = 2
    nipype_max_mem_gb = max(node.mem_gb for graph in graphs for node in graph.nodes)
    mem_mb = ceil(nipype_max_mem_gb / n_cpus * 1536)  # fudge factor
    mem_gb = float(mem_mb) / 1024.

    extra_args = ""

    str_arg_names = [
        "keep",
        "subject_exclude",
        "subject_include",
        "subject_list",
        "fs_license_file",
    ]
    for arg in str_arg_names:
        v = getattr(opts, arg, None)
        if v is not None:
            k = arg.replace("_", "-")
            extra_args += f"\\\n--{k} {v}"

    bool_arg_names = [
        "nipype_resource_monitor",
        "watchdog",
        "verbose",
    ]
    for arg in bool_arg_names:
        v = getattr(opts, arg, None)
        if v is True:
            k = arg.replace("_", "-")
            extra_args += f"\\\n--{k}"

    data = dict(
        n_chunks=n_chunks,  # one-based indexing
        singularity_container=os.environ["SINGULARITY_CONTAINER"],
        cwd=str(Path(workdir).resolve()),
        graphs_file=str(Path(workdir).resolve() / graphs_file),
        n_cpus=n_cpus,
        mem_gb=mem_gb,
        mem_mb=mem_mb,
        extra_args=extra_args,
    )

    stpaths = []
    for cluster_type, script_template in script_templates.items():
        st = script_template.format(**data)

        stpath = f"submit.{cluster_type}.sh"
        stpaths.append(f'"{stpath}"')

        with open(Path(workdir) / stpath, "w") as f:
            f.write(st)

    logger.log(25, f"Cluster submission script templates were created at {p.join(stpaths)}")
