# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from dataclasses import dataclass
from pathlib import Path

import datalad.api as dl
import openneuro as on
from halfpipe.model.file.base import File
from halfpipe.model.file.schema import FileSchema


@dataclass
class Dataset:
    name: str
    url: str
    consistency_paths: list[str]
    openneuro_id: str
    openneuro_url: str
    paths: list[str]
    osf_paths: list[str]
    # tsnr
    # tsnr_halfpipe
    # FC
    # ReHo
    # seed
    # falff
    # alff
    # dual_Based

    def download(self, tmp_path: Path) -> File:
        ds = dl.clone(source=self.url, path=str(tmp_path))
        for path in self.paths:
            ds.get(path)
        return FileSchema().load(dict(datatype="bids", path=str(tmp_path)))

    def download_openneuro(self, tmp_path: Path) -> File:
        for file_path in self.paths:
            on.download(dataset=self.openneuro_id, include=file_path, target_dir=tmp_path)
        return FileSchema().load(dict(datatype="bids", path=str(tmp_path)))


datasets: list[Dataset] = [
    Dataset(
        name="on_harmony",  # single-band scan
        openneuro_id="ds004712",
        openneuro_url="https://github.com/OpenNeuroDatasets/ds004712/blob/master",
        url="https://github.com/OpenNeuroDatasets/ds004712.git",
        paths=[
            "sub-13192/ses-NOT3GEM001/func/sub-13192_ses-NOT3GEM001_task-rest_acq-resopt2_bold.nii.gz",
            "sub-13192/ses-NOT3GEM001/anat/sub-13192_ses-NOT3GEM001_T1w.json",
            "sub-13192/ses-NOT3GEM001/anat/sub-13192_ses-NOT3GEM001_T1w.nii.gz",
        ],
        osf_paths=[
            "dataset1_onharmony/tsnr",  # placeholder tsnr
            "dataset1_onharmony/tsnr",  # placeholder tsnr_halfpipe
            "dataset1_onharmony/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv",
            "dataset1_onharmony/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-reHo_reho.nii.gz",
            "dataset1_onharmony/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-seedCorr_seed-pcc_stat-z_statmap.nii.gz",
            "dataset1_onharmony/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-fALFF_falff.nii.gz",
            "dataset1_onharmony/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-fALFF_alff.nii.gz",
            "dataset1_onharmony/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-dualReg_map-smith09_component-1_stat-z_statmap.nii.gz",
        ],
        consistency_paths=[
            "nipype/reports_wf/single_subject_13192_wf/func_preproc_ses_NOT3GEM001_task_rest_wf/func_report_wf/compute_tsnr/vol0000_xform-00000_merged_tsnr.nii.gz"
            # placeholder tsnr_halfpipe
            "derivatives/halfpipe/sub-13192/ses-NOT3GEM001/func/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv"
            "derivatives/halfpipe/sub-13192/ses-NOT3GEM001/func/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-reHo_reho.nii.gz"
            "derivatives/halfpipe/sub-13192/ses-NOT3GEM001/func/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-seedCorr_seed-pcc_stat-z_statmap.nii.gz"
            "derivatives/halfpipe/sub-13192/ses-NOT3GEM001/func/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-fALFF_falff.nii.gz"
            "derivatives/halfpipe/sub-13192/ses-NOT3GEM001/func/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-fALFF_alff.nii.gz"
            "derivatives/halfpipe/sub-13192/ses-NOT3GEM001/func/task-rest/sub-13192_ses-NOT3GEM001_task-rest_feature-dualReg_map-smith09_component-1_stat-z_statmap.nii.gz"
        ],
    ),
    # Dataset(
    #     name="emory",  # multiband
    #     openneuro_id="ds003540",
    #     openneuro_url="https://github.com/OpenNeuroDatasets/ds003540/blob/master",
    #     url="https://github.com/OpenNeuroDatasets/ds003540.git",
    #     paths=[
    #         "sub-01/anat/sub-01_T1w.nii.gz",
    #         "sub-01/func/sub-01_task-rest_acq-MB8_bold.nii.gz",
    #         "sub-01/func/sub-01_task-rest_acq-MB8_sbref.nii.gz",
    #     ],
    #     osf_paths=[
    #         "dataset2_emory/tsnr",  # placeholder tsnr
    #         "dataset2_emory/tsnr",  # placeholder tsnr_halfpipe
    #         "dataset2_emory/task-rest/sub-01_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv",
    #         "dataset2_emory/task-rest/sub-01_task-rest_feature-reHo_reho.nii.gz",
    #         "dataset2_emory/task-rest/sub-01_task-rest_feature-seedCorr_seed-pcc_stat-z_statmap.nii.gz",
    #         "dataset2_emory/task-rest/sub-01_task-rest_feature-fALFF_falff.nii.gz",
    #         "dataset2_emory/task-rest/sub-01_task-rest_feature-fALFF_alff.nii.gz",
    #         "dataset2_emory/task-rest/sub-01_task-rest_feature-dualReg_map-smith09_component-1_stat-z_statmap.nii.gz",
    #     ],
    #     consistency_paths=[
    #         "nipype/reports_wf/single_subject_01_wf/func_preproc_task_rest_wf/func_report_wf/compute_tsnr/vol0000_xform-00000_merged_tsnr.nii.gz",  # noqa: E501
    #         # placeholder tsnr_halfpipe
    #         "derivatives/halfpipe/sub-01/func/task-rest/sub-01_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv",  # noqa: E501
    #         "derivatives/halfpipe/sub-01/func/task-rest/sub-01_task-rest_feature-reHo_reho.nii.gz",
    #         "derivatives/halfpipe/sub-01/func/task-rest/sub-01_task-rest_feature-seedCorr_seed-pcc_stat-z_statmap.nii.gz",
    #         "derivatives/halfpipe/sub-01/func/task-rest/sub-01_task-rest_feature-fALFF_falff.nii.gz",
    #         "derivatives/halfpipe/sub-01/func/task-rest/sub-01_task-rest_feature-fALFF_alff.nii.gz",
    #         "derivatives/halfpipe/sub-01/func/task-rest/sub-01_task-rest_feature-dualReg_map-smith09_component-1_stat-z_statmap.nii.gz",  # noqa: E501
    #     ],
    # ),
    # Dataset(
    #     name="adhd_200_neuroimage",  # 1.5 Tesla (old)
    #     openneuro_url=None,
    #     openneuro_id=None,
    #     url="https://datasets.datalad.org/adhd200/",
    #     paths=[
    #         "RawDataBIDS/NeuroIMAGE/sub-3190461/ses-1/anat/sub-3190461_ses-1_run-1_T1w.nii.gz",
    #         "RawDataBIDS/NeuroIMAGE/sub-3190461/ses-1/func/sub-3190461_ses-1_task-rest_run-1_bold.nii.gz",
    #         "RawDataBIDS/NeuroIMAGE/task-rest_bold.json",
    #         "RawDataBIDS/NeuroIMAGE/T1w.json",
    #     ],
    #     # previous participant was 7446626, we change for 3190461
    #     osf_paths=[
    #         "dataset3_adhd/tsnr",  # placeholder tsnr
    #         "dataset3_adhd/tsnr",  # placeholder tsnr_halfpipe
    #         "dataset3_adhd/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv",  # noqa: E501
    #         "dataset3_adhd/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-reHo_reho.nii.gz" "",
    #         "dataset3_adhd/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-seedCorr_seed-pcc_stat-z_statmap.nii.gz",
    #         "dataset3_adhd/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-fALFF_falff.nii.gz",
    #         "dataset3_adhd/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-fALFF_alff.nii.gz",
    #         "dataset3_adhd/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-dualReg_map-smith09_component-1_stat-z_statmap.nii.gz", # noqa: E501
    #     ],
    #     consistency_paths=[
    #         "nipype/reports_wf/single_subject_3190461_wf/func_preproc_ses_1_task_rest_run_1_wf/func_report_wf/compute_tsnr/vol0000_xform-00000_merged_tsnr.nii.gz", # noqa: E501
    #         # placeholder tsnr_halfpipe
    #         "derivatives/halfpipe/sub-3190461/ses-1/func/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv",  # noqa: E501
    #         "derivatives/halfpipe/sub-3190461/ses-1/func/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-reHo_reho.nii.gz", # noqa: E501
    #         "derivatives/halfpipe/sub-3190461/ses-1/func/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-seedCorr_seed-pcc_stat-z_statmap.nii.gz",  # noqa: E501
    #         "derivatives/halfpipe/sub-3190461/ses-1/func/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-fALFF_falff.nii.gz",  # noqa: E501
    #         "derivatives/halfpipe/sub-3190461/ses-1/func/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-fALFF_alff.nii.gz", # noqa: E501
    #         "derivatives/halfpipe/sub-3190461/ses-1/func/task-rest/sub-3190461_ses-1_task-rest_run-1_feature-dualReg_map-smith09_component-1_stat-z_statmap.nii.gz", # noqa: E501
    #     ],
    # ),
    # Dataset(
    #     name="panikratova",  # New 1.5 Tesla
    #     openneuro_url="",
    #     openneuro_id="ds002422",
    #     url="https://github.com/OpenNeuroDatasets/ds002422",
    #     paths=[
    #         "sub-09/func/sub-09_task-rest_bold.nii.gz",
    #         "sub-09/func/sub-09_task-rest_bold.json",
    #         "sub-09/anat/sub-09_T1w.nii",
    #         "T1w.json",
    #     ],
    #     osf_paths=[
    #         # tsnr
    #         # tsnr_halfpipe
    #         # FC
    #         # ReHo
    #         # seed
    #         # falff
    #         # alff
    #         # dual_Based
    #     ],
    #     consistency_paths=[
    #         # tsnr
    #         # tsnr_halfpipe
    #         # FC
    #         # ReHo
    #         # seed
    #         # falff
    #         # alff
    #         # dual_Based
    #     ],
    # ),
    # Dataset(
    #     name="sleepy_brain",  # Has fieldmaps
    #     openneuro_id="ds000201",
    #     openneuro_url="https://github.com/OpenNeuroDatasets/ds000201/blob/master/",
    #     url="https://github.com/OpenNeuroDatasets/ds000201.git",
    #     paths=[
    #         "sub-9040/ses-1/fmap/sub-9040_ses-1_magnitude2.nii.gz",
    #         "sub-9040/ses-1/fmap/sub-9040_ses-1_magnitude1.nii.gz",
    #         "sub-9040/ses-1/fmap/sub-9040_ses-1_phase1.nii.gz",
    #         "sub-9040/ses-1/fmap/sub-9040_ses-1_phase2.nii.gz",
    #         "sub-9040/ses-1/fmap/sub-9040_ses-1_magnitude1.json",
    #         "sub-9040/ses-1/fmap/sub-9040_ses-1_magnitude2.json",
    #         "sub-9040/ses-1/fmap/sub-9040_ses-1_phase1.json",
    #         "sub-9040/ses-1/fmap/sub-9040_ses-1_phase2.json",
    #         "sub-9040/ses-1/anat/sub-9040_ses-1_T1w.json",
    #         "sub-9040/ses-1/anat/sub-9040_ses-1_T1w.nii.gz",
    #         "sub-9040/ses-1/func/sub-9040_ses-1_task-rest_bold.nii.gz",
    #         "sub-9040/ses-1/func/sub-9040_ses-1_task-rest_bold.json",
    #     ],
    #     osf_paths=[
    #         "dataset4_sleepy/tsnr",  # placeholder tsnr
    #         "dataset4_sleepy/tsnr",  # placeholder tsnr_halfpipe
    #         "dataset4_sleepy/task_rest/sub-9040_ses-1_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv",  # noqa: E501
    #         "dataset4_sleepy/task_rest/sub-9040_ses-1_task-rest_feature-reHo_reho.nii.gz",
    #         "dataset4_sleepy/task_rest/sub-9040_ses-1_task-rest_feature-seedCorr_seed-pcc_stat-z_statmap.nii.gz",
    #         "dataset4_sleepy/task_rest/sub-9040_ses-1_task-rest_feature-fALFF_falff.nii.gz",
    #         "dataset4_sleepy/task_rest/sub-9040_ses-1_task-rest_feature-fALFF_alff.nii.gz",
    #         "dataset4_sleepy/task_rest/sub-9040_ses-1_task-rest_feature-dualReg_map-smith09_component-1_stat-z_statmap.nii.gz",  # noqa: E501
    #     ],
    #     consistency_paths=[
    #         "nipype/reports_wf/single_subject_9040_wf/func_preproc_ses_1_task_rest_wf/func_report_wf/compute_tsnr/vol0000_xform-00000_merged_tsnr.nii.gz",  # noqa: E501
    #         # placeholder tsnr_halfpipe
    #         "derivatives/halfpipe/sub-9040/ses-1/func/task-rest/sub-9040_ses-1_task-rest_feature-corrMatrix_atlas-schaefer2018_desc-correlation_matrix.tsv",  # noqa: E501
    #         "derivatives/halfpipe/sub-9040/ses-1/func/task-rest/sub-9040_ses-1_task-rest_feature-reHo_reho.nii.gz",
    #         "derivatives/halfpipe/sub-9040/ses-1/func/task-rest/sub-9040_ses-1_task-rest_feature-seedCorr_seed-pcc_stat-z_statmap.nii.gz",  # noqa: E501
    #         "derivatives/halfpipe/sub-9040/ses-1/func/task-rest/sub-9040_ses-1_task-rest_feature-fALFF_falff.nii.gz",
    #         "derivatives/halfpipe/sub-9040/ses-1/func/task-rest/sub-9040_ses-1_task-rest_feature-fALFF_alff.nii.gz",
    #         "derivatives/halfpipe/sub-9040/ses-1/func/task-rest/sub-9040_ses-1_task-rest_feature-dualReg_map-smith09_component-1_stat-z_statmap.nii.gz",  # noqa: E501
    #     ],
    # ),
]
