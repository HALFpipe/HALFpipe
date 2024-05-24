# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import zipfile
from datetime import datetime
from multiprocessing import cpu_count
from pathlib import Path

import pytest
from fmriprep import config
from halfpipe.cli.parser import build_parser
from halfpipe.cli.run import run_stage_run
from halfpipe.file_index.bids import BIDSIndex
from halfpipe.model.spec import save_spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph

from .datasets import Dataset, datasets
from .spec import TestSetting, make_spec

settings_list: list[TestSetting] = [
    TestSetting(
        name="FalseComb0",
        base_setting=dict(
            confounds_removal=[],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="TrueComb0",
        base_setting=dict(
            confounds_removal=[],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="TrueComb1",
        base_setting=dict(
            confounds_removal=["a_comp_cor_0[0-4]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="TrueComb2",
        base_setting=dict(
            confounds_removal=["(trans|rot)_[xyz]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="TrueComb3",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="TrueComb4",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="TrueComb5",
        base_setting=dict(
            confounds_removal=[
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="FalseComb1",
        base_setting=dict(
            confounds_removal=["a_comp_cor_0[0-4]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="FalseComb2",
        base_setting=dict(
            confounds_removal=["(trans|rot)_[xyz]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="FalseComb3",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="FalseComb4",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="FalseComb5",
        base_setting=dict(
            confounds_removal=[
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
]


@pytest.mark.parametrize("dataset", datasets)
def test_extraction(dataset: Dataset, tmp_path: Path, pcc_mask: Path):
    """
    Run preprocessing and feature extraction for each of the four participants,
    coming from our list of datasets, then compare features to those acquired in
    reference version Halfpipe 1.2.2. Standard TSNR is calculated inside the
    fmriprep workflows. Since we do a bit more preprocessing in halfpipe,
    we calculate an extra TSNR.

    The baseline check checks that the feature extraction worked correctly.

    Consistency check flow consists of:
    # 1. Downloading the baseline files from OSF
    # 2. TODO: Comparing all features
    # 3. TODO: Visualize comparison

    Base threshold of variability should be based on running halfpipe 1000 times
    or taking fmriprep example?
    """

    dataset_file = dataset.download(tmp_path)

    spec = make_spec(dataset_files=[dataset_file], pcc_mask=pcc_mask, test_settings=settings_list)
    config.nipype.omp_nthreads = cpu_count()
    save_spec(spec, workdir=tmp_path)

    # Run built-in halfpipe
    workflow = init_workflow(tmp_path)
    graphs = init_execgraph(tmp_path, workflow)
    parser = build_parser()
    opts = parser.parse_args(args=list())
    opts.graphs = graphs
    opts.debug = True
    opts.nipype_run_plugin = "MultiProc"  # "Simple", "MultiProc"
    opts.workdir = tmp_path  # necessary when you choose MultiProc

    run_stage_run(opts)

    # OR: Run another halfpipe version
    # subprocess.call(["docker", "run", "--volume", f"{tmp_path}:{tmp_path}", "--rm", "halfpipe/halfpipe:1.2.2 "])

    # Look for derivatives for comparison and zip them
    index = BIDSIndex()
    index.put(tmp_path / "derivatives")
    spec_file = tmp_path / "spec.json"

    for sub in dataset.subject_ids:
        paths_to_zip = []
        for test_setting in settings_list:
            name = test_setting.name

            corr = index.get(sub=sub, feature=f"{name}CorrMatrix", desc="correlation", suffix="matrix")
            dual_reg = index.get(sub=sub, feature=f"{name}DualReg", suffix="statmap", stat="z", component="8")
            falff = index.get(sub=sub, feature=f"{name}FALFF", suffix="falff", extension=".nii.gz")
            alff = index.get(sub=sub, feature=f"{name}FALFF", suffix="alff", extension=".nii.gz")
            reho = index.get(sub=sub, feature=f"{name}ReHo", suffix="reho", extension=".nii.gz")
            pcc = index.get(sub=sub, feature=f"{name}SeedCorr", suffix="statmap", stat="z")

            for feature_name, feature_path in [
                ("correlation matrix", corr),
                ("dual regression", dual_reg),
                ("falff", falff),
                ("alff", alff),
                ("reho", reho),
                ("pcc", pcc),
            ]:
                assert feature_path is not None and len(feature_path) == 1, f"Missing path for {name} {feature_name}"

            paths_to_zip.extend([list(corr)[0], list(dual_reg)[0], list(falff)[0], list(alff)[0], list(reho)[0], list(pcc)[0]])

        tsnr_fmriprep = index.get(sub=sub, suffix="tsnr", datatype="func")
        paths_to_zip.extend([list(tsnr_fmriprep)[0], spec_file])

        # Create the zip file in the specified output directory
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        zip_filename = f"{dataset.openneuro_id}_sub-{sub}_time-{timestamp}.zip"
        zip_filepath = tmp_path / zip_filename
        with zipfile.ZipFile(zip_filepath, "w") as zipf:
            for file in paths_to_zip:
                zipf.write(file, arcname=file.relative_to(tmp_path))
        print(f"Created zip file: {zip_filepath}")
