# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os


def memorylimit():
    if "SLURM_MEM_PER_CPU" in os.environ and "SLURM_CPUS_PER_TASK" in os.environ:
        memory_mb = float(os.environ["SLURM_MEM_PER_CPU"]) * float(
            os.environ["SLURM_CPUS_PER_TASK"]
        )
        return memory_mb / 1024.0

    import subprocess

    try:
        proc = subprocess.Popen(
            ["bash", "-c", "ulimit -m"],
            preexec_fn=lambda: os.setpgid(0, 0),  # make the process its own process group
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        memory_kb = float(next(proc.stdout).strip())
        return memory_kb / 1024.0 / 1024.0
    except Exception:
        pass  # ignore error
