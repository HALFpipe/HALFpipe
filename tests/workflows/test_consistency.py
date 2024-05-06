# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


import os
import shutil
from multiprocessing import cpu_count
from pathlib import Path

import nibabel as nib
import pytest
from fmriprep import config
from halfpipe.cli.parser import build_parser
from halfpipe.cli.run import run_stage_run
from halfpipe.interfaces.reports.tsnr import TSNR
from halfpipe.model.spec import save_spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph

from .datasets import Dataset, datasets
from .spec import make_spec


@pytest.mark.parametrize("dataset", datasets)
def test_extraction(dataset: Dataset, tmp_path: Path, pcc_mask: Path):
    """
    Run preprocessing and feature extraction for each of the four participants,
    coming from our list of datasets, then compare features to those acquired in
    reference version Halfpipe 1.2.2. Standard TSNR is calculated inside the
    fmriprep workflows. Since we do a bit more preprocessing in halfpipe,
    we calculate an extra TSNR.

    The baseline check just checks that the feature extraction worked correctly.

    Consistency check flow consists of:
    # 1. Downloading the baseline files from OSF
    # 2. TODO: Comparing all features
    # 3. TODO: Visualize comparison

    Base threshold of variability should be based on running halfpipe 1000 times
    or taking fmriprep example?
    """

    dataset_file = dataset.download(tmp_path)

    # Need to add the option to do it with none

    counfound_comb = [
        # None,
        ["a_comp_cor_0[0-4]"],
        ["(trans|rot)_[xyz]"],
        [
            "(trans|rot)_[xyz]",
            "(trans|rot)_[xyz]_derivative1",
            "(trans|rot)_[xyz]_power2",
            "(trans|rot)_[xyz]_derivative1_power2",
        ],
        [
            "(trans|rot)_[xyz]",
            "(trans|rot)_[xyz]_derivative1",
            "(trans|rot)_[xyz]_power2",
            "(trans|rot)_[xyz]_derivative1_power2",
            "global_signal",
        ],
        ["global_signal"],
    ]

    # Iterate with an index to use in naming
    for index, c in enumerate(counfound_comb, start=1):
        spec = make_spec(dataset_files=[dataset_file], pcc_mask=pcc_mask, confounds_chosen=c, ica_aroma=False)
        config.nipype.omp_nthreads = cpu_count()

        confound_folder_name = f"comb{index}"  # Generate a folder name depending on confound
        specific_workdir = tmp_path / confound_folder_name
        os.makedirs(specific_workdir, exist_ok=True)
        save_spec(spec, workdir=specific_workdir)

        workflow = init_workflow(specific_workdir)
        graphs = init_execgraph(specific_workdir, workflow)
        parser = build_parser()
        opts = parser.parse_args(args=list())
        opts.graphs = graphs
        opts.nipype_run_plugin = "Simple"
        opts.debug = True

        raw_data = Path(specific_workdir) / "rawdata"
        has_sessions = any(raw_data.glob("sub-*/ses-*"))

        if has_sessions:
            (bold_path,) = specific_workdir.glob("rawdata/sub-*/ses-*/func/*_bold.nii.gz")
        else:
            (bold_path,) = specific_workdir.glob("rawdata/sub-*/func/*_bold.nii.gz")

        # Reorient the BOLD image and overwrite the original file
        # reorient_image(bold_path, bold_path)  # Input = output path because we are overwriting

        bold_image = nib.nifti1.load(bold_path)

        run_stage_run(opts)

        if has_sessions:
            (preproc_path,) = specific_workdir.glob("derivatives/halfpipe/sub-*/ses-*/func/*_bold.nii.gz")
        else:
            (preproc_path,) = specific_workdir.glob("derivatives/halfpipe/sub-*/func/*_bold.nii.gz")
        preproc_image = nib.nifti1.load(preproc_path)

        # Calculate extra TSNR and store on the fly
        tsnr = TSNR()
        tsnr.inputs.in_file = preproc_path
        tsnr_hp = tsnr.run()
        current_tsnr_halfpipe = tsnr_hp.outputs.out_file
        output_dir = os.path.dirname(preproc_path)  # Extracting directory from the file path
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, "tsnr_halfpipe.nii.gz")  # Define the full path for new TSNR
        shutil.copy(current_tsnr_halfpipe, output_file_path)  # Ccopy into new location

        ############   Baseline check   ##########
        assert bold_image.shape[3] == preproc_image.shape[3]

        # ############ Consistency checks ##########
        # setup_test_resources()
        # zip_path = get_resource("halfpipe122_baseline.zip")  # this will be done 1 time per dataset, split test?

        # with ZipFile(zip_path) as zip_file:
        #     zip_file.extractall(tmp_path)

        # baseline_path = tmp_path / "halfpipe122_baseline"
        # assert isinstance(baseline_path, Path), "Baseline path did not return a Path object."
        # assert any(baseline_path.iterdir()), "The extracted directory is empty."

        # # Establish paths for all relevant files for comparison
        # base_paths = [baseline_path / path for path in dataset.osf_paths]
        # current_paths = [tmp_path / path for path in dataset.consistency_paths]
        # base_tsnr, base_fc, base_reho, base_seed, base_falff, base_alff, base_dual = base_paths
        # current_tsnr, current_fc, current_reho, current_seed, current_falff, current_alff, current_dual = current_paths
        # #! add base_tsnr_halfpipe
        # #! add current_tsnr_halfpipe

        # # threshold = 0.3  # Example threshold?
        # fc_fig, mean_abs_diff = compare_fcs(base_fc, current_fc)

        # # assert mean_abs_diff < threshold, "Mean absolute difference is too high"
