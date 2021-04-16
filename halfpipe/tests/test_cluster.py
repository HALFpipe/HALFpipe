# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path
from collections import namedtuple, OrderedDict

from ..cli.parser import _build_parser
from ..cluster import create_example_script


def test_create_example_script(tmp_path: Path):
    NodePlaceholder = namedtuple("NodePlaceholder", ["mem_gb"])
    WorkflowPlaceholder = namedtuple("WorkflowPlaceholder", ["uuid", "nodes"])

    parser = _build_parser()
    opts = parser.parse_args(["--verbose"])

    node = NodePlaceholder(mem_gb=1.2)
    graphs = OrderedDict([
        ("a", WorkflowPlaceholder(uuid="aaa", nodes=[node])),
        ("b", WorkflowPlaceholder(uuid="aaa", nodes=[node])),
        ("model", WorkflowPlaceholder(uuid="aaa", nodes=[node])),
    ])

    previous_singularity_container = os.environ.get("SINGULARITY_CONTAINER")
    os.environ["SINGULARITY_CONTAINER"] = "halfpipe.sif"

    create_example_script(tmp_path, graphs, opts)

    if previous_singularity_container is None:
        del os.environ["SINGULARITY_CONTAINER"]
    else:
        os.environ["SINGULARITY_CONTAINER"] = previous_singularity_container

    assert Path(tmp_path / "submit.slurm.sh").is_file()
    assert Path(tmp_path / "submit.sge.sh").is_file()
    assert Path(tmp_path / "submit.torque.sh").is_file()
