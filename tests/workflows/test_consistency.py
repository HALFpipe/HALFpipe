# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from multiprocessing import cpu_count
from pathlib import Path

import nibabel as nib
import pytest
from fmriprep import config
from halfpipe.cli.parser import build_parser
from halfpipe.cli.run import run_stage_run
from halfpipe.model.spec import save_spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph

from .datasets import Dataset, datasets
from .spec import make_spec


# Parametrize according to consistency_specs
@pytest.mark.parametrize("dataset", datasets)
def test_extraction(dataset: Dataset, tmp_path: Path, pcc_mask: Path):
    """
    Run preprocessing and feature extraction for each of the four participants,
    coming from our list of datasets, then compare those to
    #TODO ENHANCEMENT: Instead of using parametrization of fixtures, do function calls.
    """

    dataset_file = dataset.download(tmp_path)

    spec = make_spec(
        dataset_files=[dataset_file],
        pcc_mask=pcc_mask,
    )

    config.nipype.omp_nthreads = cpu_count()
    save_spec(spec, workdir=tmp_path)

    workflow = init_workflow(tmp_path)

    graphs = init_execgraph(tmp_path, workflow)
    # graph = next(iter(graphs.values()))

    # sdc_estimate only relevant for datasets with fieldmaps
    # assert any("sdc_estimate_wf" in u.fullname for u in graph.nodes)

    parser = build_parser()
    opts = parser.parse_args(args=list())

    opts.graphs = graphs
    opts.nipype_run_plugin = "Simple"
    opts.debug = True

    raw_data = Path(tmp_path) / "rawdata"
    has_sessions = any(raw_data.glob("sub-*/ses-*"))

    if has_sessions:
        (bold_path,) = tmp_path.glob("rawdata/sub-*/ses-*/func/*_bold.nii.gz")
    else:
        (bold_path,) = tmp_path.glob("rawdata/sub-*/func/*_bold.nii.gz")
    bold_image = nib.nifti1.load(bold_path)

    run_stage_run(opts)

    if has_sessions:
        (preproc_path,) = tmp_path.glob("derivatives/halfpipe/sub-*/ses-*/func/*_bold.nii.gz")
    else:
        (preproc_path,) = tmp_path.glob("derivatives/halfpipe/sub-*/func/*_bold.nii.gz")
    preproc_image = nib.nifti1.load(preproc_path)

    ####### Baseline checks ##########
    assert bold_image.shape[3] == preproc_image.shape[3] + skip_vols

    ####### Consistency checks ##########
    # 1. Download the baseline files from OSF
    # 2. Comparison code

    # Visualization - different
