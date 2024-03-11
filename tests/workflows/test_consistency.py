# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from multiprocessing import cpu_count

import pytest
from fmriprep import config
from halfpipe.cli.parser import build_parser
from halfpipe.cli.run import run_stage_run
from halfpipe.model.spec import save_spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph

from .datasets import datasets


# Parametrize according to consistency_specs
@pytest.mark.parametrize("consistency_spec", datasets, indirect=True)
def test_extraction(consistency_spec, tmp_path):
    """
    Run preprocessing and feature extraction for each of the three participants
    """

    skip_vols = 3
    consistency_spec.global_settings.update(dict(dummy_scans=skip_vols))
    config.nipype.omp_nthreads = cpu_count()
    save_spec(consistency_spec, workdir=tmp_path)

    workflow = init_workflow(tmp_path)

    graphs = init_execgraph(tmp_path, workflow)
    # graph = next(iter(graphs.values()))

    # does sdc_estimate only relevant for datasets with fieldmaps
    # assert any("sdc_estimate_wf" in u.fullname for u in graph.nodes)

    parser = build_parser()
    opts = parser.parse_args(args=list())

    opts.graphs = graphs
    opts.nipype_run_plugin = "Simple"
    opts.debug = True

    run_stage_run(opts)

    # Add checks
