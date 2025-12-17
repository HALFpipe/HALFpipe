# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import tarfile
from datetime import datetime
from multiprocessing import cpu_count
from pathlib import Path

import pytest
import zstandard
from fmriprep import config

from halfpipe.cli.parser import build_parser
from halfpipe.cli.run import run_stage_run
from halfpipe.file_index.bids import BIDSIndex
from halfpipe.logging import logger
from halfpipe.model.spec import save_spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph

from .datasets import Dataset, datasets
from .spec import TestSetting, make_spec

settings_list: list[TestSetting] = [
    TestSetting(
        name="baseline",  # was FalseComb0
        base_setting=dict(
            confounds_removal=[],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="icaAroma",  # was TrueComb0
        base_setting=dict(
            confounds_removal=[],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="icaAromaCCompCor",  # was TrueComb1
        base_setting=dict(
            confounds_removal=["c_comp_cor_0[0-4]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="icaAromaACompCor",
        base_setting=dict(
            confounds_removal=["a_comp_cor_0[0-4]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="icaAromaMotionParameters6",  # was TrueComb2
        base_setting=dict(
            confounds_removal=["(trans|rot)_[xyz]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="icaAromaMotionParameters",  # was TrueComb3
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
        name="icaAromaMotionParametersGSR",  # was TrueComb4
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
        name="icaAromaGSR",  # was TrueComb5
        base_setting=dict(
            confounds_removal=["global_signal"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="icaAromaScrubbing",
        base_setting=dict(
            confounds_removal=["motion_outlier[0-9]+"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    TestSetting(
        name="icaAromaScrubbingGSR",
        base_setting=dict(
            confounds_removal=[
                "motion_outlier[0-9]+",
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
    # cCompCor = CSF
    # aCompCor = CSF + White matter.
    TestSetting(
        name="cCompCor",  # was FalseComb1
        base_setting=dict(
            confounds_removal=["c_comp_cor_0[0-4]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="aCompCor",
        base_setting=dict(
            confounds_removal=["a_comp_cor_0[0-4]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="motionParameters6",  # was FalseComb2
        base_setting=dict(
            confounds_removal=["(trans|rot)_[xyz]"],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="motionParameters",  # was FalseComb3
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
        name="motionParametersGSR",  # was FalseComb4
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
        name="GSR",  # was FalseComb5
        base_setting=dict(
            confounds_removal=[
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="motionParametersScrubbing",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "motion_outlier[0-9]+",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="motionParametersScrubbingGSR",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "motion_outlier[0-9]+",
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="Wang2023Simple",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "white_matter",
                "csf",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="Wang2023SimpleGSR",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "white_matter",
                "csf",
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="Wang2023Scrubbing",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "white_matter",
                "csf",
                "motion_outlier[0-9]+",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="Wang2023ScrubbingGSR",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "white_matter",
                "csf",
                "motion_outlier[0-9]+",
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="Wang2023ACompCor",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "a_comp_cor_0[0-4]",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="Wang2023ACompCorGSR",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "a_comp_cor_0[0-4]",
                "global_signal"
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=False,
        ),
    ),
    TestSetting(
        name="everything",
        base_setting=dict(
            confounds_removal=[
                "(trans|rot)_[xyz]",
                "(trans|rot)_[xyz]_derivative1",
                "(trans|rot)_[xyz]_power2",
                "(trans|rot)_[xyz]_derivative1_power2",
                "motion_outlier[0-9]+",
                "white_matter",
                "csf",
                "c_comp_cor_0[0-4]",
                "global_signal",
            ],
            grand_mean_scaling=dict(mean=10000.0),
            ica_aroma=True,
        ),
    ),
]

@pytest.mark.parametrize("dataset", datasets)
def test_extraction(dataset: Dataset, tmp_path: Path, pcc_mask: Path):
    """
    Run preprocessing and feature extraction for each of the participants coming the list of datasets,
    and each of the settings coming from settings_list. Standard TSNR is calculated inside thefmriprep workflows.
    We create a zip file with all the features, tsnr and spec file, per participant.
    """

    dataset_file = dataset.download(tmp_path)
    spec = make_spec(dataset_files=[dataset_file], pcc_mask=pcc_mask, test_settings=settings_list)
    spec.features = [feature for feature in spec.features if feature.type != "gig_ica"]  # Drop gig-ica feature
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
    # OR: Run another halfpipe version (not implemented)
    # subprocess.call(["docker", "run", "--volume", f"{tmp_path}:{tmp_path}", "--rm", "halfpipe/halfpipe:1.2.2 "])

    index = BIDSIndex()
    index.put(tmp_path / "derivatives")
    spec_file = tmp_path / "spec.json"

    for sub in dataset.subject_ids:
        paths_to_zip = []
        for test_setting in settings_list:
            name = test_setting.name

            for title, kwargs in [
                ("Timeseries", dict(sub=sub, feature=f"{name}CorrMatrix", suffix="timeseries", extension=".tsv")),
                ("Correlation matrix", dict(sub=sub, feature=f"{name}CorrMatrix", suffix="matrix", desc="correlation")),
                ("Dual regression", dict(sub=sub, feature=f"{name}DualReg", component="8", stat="z")),
                (
                    "Dualreg sidecar",
                    dict(sub=sub, feature=f"{name}DualReg", suffix="statmap", stat="effect", component="8", extension=".json"),
                ),
                ("fALFF", dict(sub=sub, feature=f"{name}FALFF", suffix="falff", extension=".nii.gz")),
                ("fALFF sidecar", dict(sub=sub, feature=f"{name}FALFF", suffix="falff", extension=".json")),
                ("Alff", dict(sub=sub, feature=f"{name}FALFF", suffix="alff", extension=".nii.gz")),
                ("Alff sidecar", dict(sub=sub, feature=f"{name}FALFF", suffix="alff", extension=".json")),
                ("ReHo", dict(sub=sub, feature=f"{name}ReHo", suffix="reho", extension=".nii.gz")),
                ("ReHo sidecar", dict(sub=sub, feature=f"{name}ReHo", suffix="reho", extension=".json")),
                ("Seed connectivity", dict(sub=sub, feature=f"{name}SeedCorr", suffix="statmap", stat="z")),
                (
                    "Seed connectivity sidecar",
                    dict(sub=sub, feature=f"{name}SeedCorr", suffix="statmap", stat="effect", extension=".json"),
                ),
            ]:
                feature_path = index.get(**kwargs)
                if feature_path is None or len(feature_path) != 1:
                    raise ValueError(f"Incorrect path for {name} {title}: {feature_path}")
                paths_to_zip.extend(list(feature_path))

        # Search for files we want to save at the subject level and save to list
        tsnr_fmriprep = index.get(sub=sub, suffix="boldmap", datatype="func", stat="tsnr")
        confounds_sidecar = index.get(sub=sub, suffix="timeseries", datatype="func", desc="confounds", extension=".json")
        confounds = index.get(sub=sub, suffix="timeseries", datatype="func", desc="confounds", extension=".tsv")
        reports_folder = tmp_path / "reports" / f"sub-{sub}"

        report_figures: list[Path] = []
        if reports_folder.exists():
            report_figures = [f for f in reports_folder.rglob("*") if f.is_file()]

        paths_to_zip.extend(list(tsnr_fmriprep or []))
        paths_to_zip.append(spec_file)
        paths_to_zip.extend(list(confounds or []))
        paths_to_zip.extend(list(confounds_sidecar or []))
        paths_to_zip.extend(report_figures)

        # Create the zstandard-compressed tar file in the specified output directory
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_filename = f"{dataset.openneuro_id}_sub-{sub}_time-{timestamp}.tar.zst"
        archive_filepath = tmp_path / archive_filename
        compressor = zstandard.ZstdCompressor(level=22, threads=24)
        with (
            archive_filepath.open("wb") as file_handle,
            compressor.stream_writer(file_handle) as compression_handle,
            tarfile.open(mode="w|", fileobj=compression_handle) as tar_file,
        ):
            for file in paths_to_zip:
                # Ensure file is a Path instance and convert it to string if needed
                if not isinstance(file, Path):
                    raise TypeError(f"Unexpected type for file: {type(file)}")
                tar_file.add(file, arcname=str(file.relative_to(tmp_path)))

        logger.info(f"Created archive file: {archive_filepath}")
