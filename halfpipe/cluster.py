# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from math import ceil
from pathlib import Path
from typing import Any, Dict, List

from .utils import inflect_engine as p
from .utils import logger
from .workflows.execgraph import filter_subjects

shebang = """#!/bin/bash
#
#
"""

cluster_configs = dict(
    slurm="""#SBATCH --job-name=halfpipe
#SBATCH --output=halfpipe.log.txt
#
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={n_cpus:d}
#SBATCH --mem={mem_mb:d}M
#
#SBATCH --array=1-{n_chunks:d}
""",
    torque="""#PBS -N halfpipe
#PBS -j oe
#PBS -o halfpipe.log.txt
#
#PBS -l nodes=1:ppn={n_cpus:d}
#PBS -l walltime=24:00:00
#PBS -l mem={mem_mb:d}mb
#
#PBS -J 1-{n_chunks:d}
""",
    sge="""#$ -N halfpipe
#$ -j y
#$ -o halfpipe.log.txt
#$ -cwd
#
#$ -pe smp {n_cpus:d}
#$ -l h_rt=24:0:0
#$ -l mem={mem_mb:d}M
#
#$ -t 1-{n_chunks:d}
""",
)

array_index_variables = dict(
    slurm="SLURM_ARRAY_TASK_ID",
    torque="PBS_ARRAY_INDEX",
    sge="SGE_TASK_ID",
)

singularity_command = """
if ! [ -x "$(command -v singularity)" ]; then
module load singularity
fi

singularity run \\
--contain --cleanenv {bind_args} \\
{singularity_container} \\
--workdir {cwd} \\
--only-run \\
--uuid {uuid_str} \\
--subject-chunks \\
--only-chunk-index ${{{array_index_variable}}} \\
--nipype-n-procs 2 {extra_args}

"""


def create_example_script(workdir, graphs: Dict[str, Any], opts):
    first_workflow = next(iter(graphs.values()))
    uuid = first_workflow.uuid

    subjects: List[str] = sorted(graphs.keys())
    subjects = filter_subjects(subjects, opts)

    n_chunks = len(subjects)
    assert n_chunks > 0

    n_cpus = 2
    mem_gb: float = (
        max(node.mem_gb for subject in subjects for node in graphs[subject].nodes) * 1.5
        + 3.0
    )  # three gigabytes for the python process plus the actual memory
    mem_mb: int = int(ceil(mem_gb * 1024))

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
            if isinstance(v, str):
                extra_args += f"\\\n--{k} {v} "
            elif isinstance(v, list):
                for d in v:
                    assert isinstance(d, str)
                    extra_args += f"\\\n--{k} '{d}' "

    bool_arg_names = [
        "nipype_resource_monitor",
        "watchdog",
        "verbose",
    ]
    for arg in bool_arg_names:
        v = getattr(opts, arg, None)
        if v is True:
            k = arg.replace("_", "-")
            extra_args += f"\\\n--{k} "

    data = dict(
        n_chunks=n_chunks,  # one-based indexing
        singularity_container=os.environ["SINGULARITY_CONTAINER"],
        cwd=str(Path(workdir).resolve()),
        uuid_str=str(uuid)[:8],
        n_cpus=n_cpus,
        mem_gb=mem_gb,
        mem_mb=mem_mb,
        extra_args=extra_args,
        bind_args="",
    )

    if opts.fs_root is not None and opts.fs_root != "/":
        data["bind_args"] = f"\\\n--bind /:{opts.fs_root}"

    stpaths = []
    for cluster_type, cluster_config in cluster_configs.items():
        data["array_index_variable"] = array_index_variables[cluster_type]

        st: str = shebang + cluster_config.format(**data)
        st += singularity_command.format(**data)

        stpath = f"submit.{cluster_type}.sh"
        stpaths.append(f'"{stpath}"')

        with open(Path(workdir) / stpath, "w") as f:
            f.write(st)

    logger.log(
        25, f"Cluster submission script templates were created at {p.join(stpaths)}"
    )
