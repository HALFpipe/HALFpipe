# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from multiprocessing import cpu_count
from pathlib import Path
from zipfile import ZipFile

import nibabel as nib
import pytest
from fmriprep import config
from halfpipe.cli.parser import build_parser
from halfpipe.cli.run import run_stage_run
from halfpipe.model.spec import save_spec
from halfpipe.resource import get as get_resource
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph

from tests.workflows.utils_consistency import compare_fcs

from ..resource import setup as setup_test_resources
from .datasets import Dataset, datasets
from .spec import make_spec


@pytest.mark.parametrize("dataset", datasets)
def test_extraction(dataset: Dataset, tmp_path: Path, pcc_mask: Path):
    """
    Run preprocessing and feature extraction for each of the four participants,
    coming from our list of datasets, then compare those to those acquired in
    reference version Halfpipe 1.2.2. The baseline check just checks
    that the feature extraction worked correctly.

    Consistency check flow consist of:
    # 1. Downloading the baseline files from OSF
    # 2. TODO: Comparing all features
    # 3. TODO: Visualize comparison

    Remains to be decided whether we want to split test or not.
    Base threshold of variability should be based on running halfpipe 1000 times
    or taking fmriprep example?
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

    ############   Baseline check   ##########
    assert bold_image.shape[3] == preproc_image.shape[3]

    ############ Consistency checks ##########
    setup_test_resources()
    zip_path = get_resource("halfpipe122_baseline.zip")  # this will be done 1 time per dataset, split?

    with ZipFile(zip_path) as zip_file:
        zip_file.extractall(tmp_path)

    baseline_path = tmp_path / "halfpipe122_baseline"
    assert isinstance(baseline_path, Path), "Baseline path did not return a Path object."
    assert any(baseline_path.iterdir()), "The extracted directory is empty."

    # Compare FCs logic
    if dataset.name == "on_harmony":
        base_fc = (
            baseline_path
            / "dataset1_onharmony"
            / "task_rest"
            / "sub-9040_ses-1_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv"
        )
        current_fc = (
            tmp_path
            / "derivatives"
            / "halfpipe"
            / "sub-9040"
            / "ses-1"
            / "func"
            / "task-rest"
            / "sub-9040_ses-1_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv"
        )
        # add extra features here
    elif dataset.name == "emory":
        base_fc = (
            baseline_path
            / "dataset2_emory"
            / "task_rest"
            / "sub-01_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv"
        )
        current_fc = (
            tmp_path
            / "derivatives"
            / "halfpipe"
            / "sub-01"
            / "func"
            / "task-rest"
            / "sub-01_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv"
        )
        # add...
    # finish for all datasets

    fc_fig, mean_abs_diff = compare_fcs(base_fc, current_fc)
    threshold = 0.3  # Example threshold?
    assert mean_abs_diff < threshold, "Mean absolute difference is too high"
