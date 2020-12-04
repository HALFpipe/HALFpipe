# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import pytest

import os
from zipfile import ZipFile
from pathlib import Path

import nibabel as nib
from nilearn.image import new_img_like

from nipype.pipeline import plugins as nip

from ...tests.resource import setup as setuptestresources
from ...resource import get as getresource
from templateflow.api import get as gettemplate

from ..base import init_workflow
from ..execgraph import init_execgraph
from ...model import FeatureSchema, FileSchema, SettingSchema, SpecSchema, savespec
from ...utils import first


@pytest.fixture(scope="module")
def bids_data(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="bids_data")

    os.chdir(str(tmp_path))

    setuptestresources()
    inputtarpath = getresource("bids_data.zip")

    with ZipFile(inputtarpath) as fp:
        fp.extractall(tmp_path)

    return tmp_path


@pytest.fixture(scope="module")
def pcc_mask(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="pcc_mask")

    os.chdir(str(tmp_path))

    atlas_img = nib.load(
        Path(os.environ["FSLDIR"]) / "data" / "atlases" / "HarvardOxford" / "HarvardOxford-cort-prob-2mm.nii.gz"
    )
    atlas = atlas_img.get_fdata()

    pcc_mask = atlas[..., 29] > 10

    pcc_mask_img = new_img_like(atlas_img, pcc_mask, copy_header=True)

    pcc_mask_fname = Path.cwd() / "pcc.nii.gz"
    nib.save(pcc_mask_img, pcc_mask_fname)

    return pcc_mask_fname


def test_feature_extraction(tmp_path, bids_data, pcc_mask):
    spec_schema = SpecSchema()
    spec = spec_schema.load(spec_schema.dump({}), partial=True)

    spec.files = list(map(FileSchema().load, [
        dict(datatype="bids", path=str(bids_data)),
        dict(
            datatype="ref",
            suffix="map",
            tags=dict(desc="smith09"),
            path=str(getresource("PNAS_Smith09_rsn10.nii.gz")),
            metadata=dict(space="MNI152NLin6Asym"),
        ),
        dict(
            datatype="ref",
            suffix="seed",
            tags=dict(desc="pcc"),
            path=str(pcc_mask),
            metadata=dict(space="MNI152NLin6Asym"),
        ),
        dict(
            datatype="ref",
            suffix="atlas",
            tags=dict(desc="schaefer2018"),
            path=str(gettemplate(
                "MNI152NLin2009cAsym",
                resolution=2,
                atlas="Schaefer2018",
                desc="400Parcels17Networks",
                suffix="dseg",
            )),
            metadata=dict(space="MNI152NLin6Asym"),
        ),
    ]))

    setting_base = dict(
        confounds_removal=[],
        grand_mean_scaling=dict(mean=10000.0),
        ica_aroma=True,
    )

    spec.settings = list(map(SettingSchema().load, [
        dict(
            name="dualRegAndSeedCorrSetting",
            output_image=False,
            bandpass_filter=dict(type="gaussian", hp_width=125.0),
            smoothing=dict(fwhm=6.0),
            **setting_base,

        ),
        dict(
            name="fALFFUnfilteredSetting",
            output_image=False,
            **setting_base,
        ),
        dict(
            name="fALFFAndReHoAndCorrMatrixSetting",
            output_image=False,
            bandpass_filter=dict(type="frequency_based", low=0.01, high=0.1),
            **setting_base,
        ),
    ]))

    spec.features = list(map(FeatureSchema().load, [
        dict(
            name="seedCorr",
            type="seed_based_connectivity",
            seeds=["pcc"],
            setting="dualRegAndSeedCorrSetting"
        ),
        dict(
            name="dualReg",
            type="dual_regression",
            maps=["smith09"],
            setting="dualRegAndSeedCorrSetting"
        ),
        dict(
            name="corrMatrix",
            type="atlas_based_connectivity",
            atlases=["schaefer2018"],
            setting="fALFFAndReHoAndCorrMatrixSetting"
        ),
        dict(
            name="reHo",
            type="reho",
            setting="fALFFAndReHoAndCorrMatrixSetting",
            smoothing=dict(fwhm=6.0),
        ),
        dict(
            name="fALFF",
            type="falff",
            setting="fALFFAndReHoAndCorrMatrixSetting",
            unfiltered_setting="fALFFUnfilteredSetting",
            smoothing=dict(fwhm=6.0),
        ),
    ]))

    spec.global_settings = dict(sloppy=True)

    savespec(spec, workdir=tmp_path)

    workflow = init_workflow(tmp_path)
    execgraphs = init_execgraph(tmp_path, workflow)

    execgraph = execgraphs[0]

    runner = nip.LinearPlugin(plugin_args=dict(
        stop_on_first_crash=True,
    ))

    firstnode = first(execgraph.nodes())

    runner.run(execgraph, updatehash=False, config=firstnode.config)
