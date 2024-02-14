# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict, namedtuple
from pathlib import Path
from typing import Any
from typing import OrderedDict as OrderedDictT
from uuid import uuid4

import pytest
from halfpipe.cli.parser import build_parser
from halfpipe.cluster import make_script


@pytest.mark.parametrize("has_model", [True, False])
def test_make_script(monkeypatch, tmp_path: Path, has_model: bool):
    NodePlaceholder = namedtuple("NodePlaceholder", ["mem_gb"])
    WorkflowPlaceholder = namedtuple("WorkflowPlaceholder", ["uuid", "nodes"])

    parser = build_parser()
    opts = parser.parse_args(["--verbose"])

    node = NodePlaceholder(mem_gb=1.2)
    graphs: OrderedDictT[str, Any] = OrderedDict(
        [
            ("a", WorkflowPlaceholder(uuid=uuid4(), nodes=[node])),
            ("b", WorkflowPlaceholder(uuid=uuid4(), nodes=[node])),
        ]
    )

    if has_model:
        graphs["model"] = WorkflowPlaceholder(uuid=uuid4(), nodes=[node])

    monkeypatch.setenv("SINGULARITY_CONTAINER", "halfpipe.sif")
    make_script(tmp_path, graphs, opts)

    assert Path(tmp_path / "submit.slurm.sh").is_file()
    assert Path(tmp_path / "submit.sge.sh").is_file()
    assert Path(tmp_path / "submit.torque.sh").is_file()
