# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
import pytest
from nipype.pipeline import plugins as nip

from halfpipe.plugins.multiproc import MultiProcPlugin
from halfpipe.workflows.fmriprep import get_fmriprep_wf_name


class DontRunRunner:
    plugin_args: dict[str, Any] = dict()

    def run(self, *args, **kwargs):
        pass


def add(a, b):
    return a + b


def make_execgraph_node(tmp_path: Path, parent_name: str) -> pe.Node:
    wf = pe.Workflow("nipype", base_dir=tmp_path)
    parent = pe.Workflow(parent_name)
    node = pe.Node(niu.Function(function=add, input_names=["a", "b"], output_names="c"), name="x")
    node.inputs.a = 1
    node.inputs.b = 2
    parent.add_nodes([node])
    wf.add_nodes([parent])

    execgraph = wf.run(plugin=DontRunRunner())
    (execnode,) = execgraph.nodes()
    return execnode


@pytest.mark.parametrize("parent_name", [get_fmriprep_wf_name(), "ica_aroma_components_wf"])
def test_keep_some_preserves_outputs(tmp_path: Path, parent_name: str):
    os.chdir(str(tmp_path))
    node = make_execgraph_node(tmp_path, parent_name)
    assert parent_name in node.fullname

    plugin = MultiProcPlugin(plugin_args=dict(keep="some", workdir=str(tmp_path), n_procs=1))
    try:
        plugin.procs = [node]
        plugin._rt = MagicMock()

        with patch.object(nip.MultiProcPlugin, "_task_finished_cb"):
            plugin._task_finished_cb(0)

        (_, unmark), _ = plugin._rt.set_node_complete.call_args
        assert unmark is False, f'--keep some would delete outputs of "{node.fullname}"'
    finally:
        plugin.pool.shutdown()
