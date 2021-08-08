# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from collections import namedtuple, OrderedDict

from ..cli.parser import build_parser
from ..cluster import create_example_script


def test_create_example_script(monkeypatch, tmp_path: Path):
    NodePlaceholder = namedtuple("NodePlaceholder", ["mem_gb"])
    WorkflowPlaceholder = namedtuple("WorkflowPlaceholder", ["uuid", "nodes"])

    parser = build_parser()
    opts = parser.parse_args(["--verbose"])

    node = NodePlaceholder(mem_gb=1.2)
    graphs = OrderedDict([
        ("a", WorkflowPlaceholder(uuid="aaa", nodes=[node])),
        ("b", WorkflowPlaceholder(uuid="aaa", nodes=[node])),
        ("model", WorkflowPlaceholder(uuid="aaa", nodes=[node])),
    ])

    monkeypatch.setenv("SINGULARITY_CONTAINER", "halfpipe.sif")
    create_example_script(tmp_path, graphs, opts)

    assert Path(tmp_path / "submit.slurm.sh").is_file()
    assert Path(tmp_path / "submit.sge.sh").is_file()
    assert Path(tmp_path / "submit.torque.sh").is_file()
