# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import tarfile
from copy import deepcopy
from math import inf
from pathlib import Path
from random import choices, normalvariate, seed
from zipfile import ZipFile

import nibabel as nib
import pandas as pd
import pytest
from halfpipe.ingest.database import Database
from halfpipe.model.feature import FeatureSchema
from halfpipe.model.file.schema import FileSchema
from halfpipe.model.setting import SettingSchema
from halfpipe.model.spec import Spec, SpecSchema
from halfpipe.resource import get as get_resource
from halfpipe.utils.image import nvol
from nilearn.image import new_img_like
from templateflow.api import get as get_template

from ..resource import setup as setup_test_resources


@pytest.fixture(scope="package")
def bids_data(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="bids_data")

    os.chdir(str(tmp_path))

    setup_test_resources()
    input_path = get_resource("bids_data.zip")

    with ZipFile(input_path) as fp:
        fp.extractall(tmp_path)

    bids_data_path = tmp_path / "bids_data"

    func_path = bids_data_path / "sub-1012" / "func"

    Path(func_path / "sub-1012_task-rest_events.tsv").unlink()  # this file is empty

    bold_file = func_path / "sub-1012_task-rest_bold.nii.gz"
    bold_img = nib.nifti1.load(bold_file)
    bold_data = bold_img.get_fdata()[..., :64]  # we don't need so many volumes for testing
    bold_img = new_img_like(bold_img, bold_data, copy_header=True)
    nib.loadsave.save(bold_img, bold_file)

    return bids_data_path


@pytest.fixture(scope="module")
def task_events(tmp_path_factory, bids_data):
    tmp_path = tmp_path_factory.mktemp(basename="task_events")

    os.chdir(str(tmp_path))

    seed(a=0x5E6128C4)

    spec_schema = SpecSchema()
    spec = spec_schema.load(spec_schema.dump({}), partial=True)
    assert isinstance(spec, Spec)

    spec.files = list(
        map(
            FileSchema().load,
            [
                dict(datatype="bids", path=str(bids_data)),
            ],
        )
    )

    database = Database(spec)

    bold_file_paths = database.get(datatype="func", suffix="bold")
    assert database.fillmetadata("repetition_time", bold_file_paths)

    scan_duration = inf
    for b in bold_file_paths:
        repetition_time = database.metadata(b, "repetition_time")
        assert isinstance(repetition_time, float)
        scan_duration = min(nvol(b) * repetition_time, scan_duration)

    onset = []
    duration = []

    t = 0.0
    d = 5.0
    while True:
        t += d
        t += abs(normalvariate(0, 1)) + 1.0  # jitter

        if t < scan_duration:
            onset.append(t)
            duration.append(d)
        else:
            break

    n = len(duration)
    trial_type = choices(["a", "b"], k=n)

    events = pd.DataFrame(dict(onset=onset, duration=duration, trial_type=trial_type))

    events_fname = Path.cwd() / "events.tsv"
    events.to_csv(events_fname, sep="\t", index=False, header=True)

    return events_fname


@pytest.fixture(scope="module")
def atlas_harvard_oxford(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(basename="pcc_mask")

    os.chdir(str(tmp_path))

    inputtarpath = get_resource("HarvardOxford.tgz")

    with tarfile.open(inputtarpath) as fp:
        fp.extractall(tmp_path)

    maps = {
        m: (tmp_path / "data" / "atlases" / "HarvardOxford" / f"HarvardOxford-{m}.nii.gz")
        for m in ("cort-prob-1mm", "cort-prob-2mm", "sub-prob-1mm", "sub-prob-2mm")
    }
    return maps


@pytest.fixture(scope="module")
def pcc_mask(tmp_path_factory, atlas_harvard_oxford):
    tmp_path = tmp_path_factory.mktemp(basename="pcc_mask")

    os.chdir(str(tmp_path))

    atlas_img = nib.nifti1.load(atlas_harvard_oxford["cort-prob-2mm"])
    atlas = atlas_img.get_fdata()

    pcc_mask = atlas[..., 29] > 10

    pcc_mask_img = new_img_like(atlas_img, pcc_mask, copy_header=True)

    pcc_mask_fname = Path.cwd() / "pcc.nii.gz"
    nib.loadsave.save(pcc_mask_img, pcc_mask_fname)

    return pcc_mask_fname


@pytest.fixture(scope="function")
def mock_spec(bids_data, task_events, pcc_mask):
    spec_schema = SpecSchema()
    spec = spec_schema.load(spec_schema.dump(dict()), partial=True)  # get defaults
    assert isinstance(spec, Spec)

    spec.files = list(
        map(
            FileSchema().load,
            [
                dict(datatype="bids", path=str(bids_data)),
                dict(
                    datatype="func",
                    suffix="events",
                    extension=".tsv",
                    tags=dict(task="rest"),
                    path=str(task_events),
                    metadata=dict(units="seconds"),
                ),
                dict(
                    datatype="ref",
                    suffix="map",
                    extension=".nii.gz",
                    tags=dict(desc="smith09"),
                    path=str(get_resource("PNAS_Smith09_rsn10.nii.gz")),
                    metadata=dict(space="MNI152NLin6Asym"),
                ),
                dict(
                    datatype="ref",
                    suffix="seed",
                    extension=".nii.gz",
                    tags=dict(desc="pcc"),
                    path=str(pcc_mask),
                    metadata=dict(space="MNI152NLin6Asym"),
                ),
                dict(
                    datatype="ref",
                    suffix="atlas",
                    extension=".nii.gz",
                    tags=dict(desc="schaefer2018"),
                    path=str(
                        get_template(
                            "MNI152NLin2009cAsym",
                            resolution=2,
                            atlas="Schaefer2018",
                            desc="400Parcels17Networks",
                            suffix="dseg",
                        )
                    ),
                    metadata=dict(space="MNI152NLin2009cAsym"),
                ),
            ],
        )
    )

    setting_base = dict(
        confounds_removal=["(trans|rot)_[xyz]"],
        grand_mean_scaling=dict(mean=10000.0),
        ica_aroma=True,
    )

    spec.settings = list(
        map(
            SettingSchema().load,
            [
                dict(
                    name="dualRegAndSeedCorrAndTaskBasedSetting",
                    output_image=True,
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
            ],
        )
    )

    spec.features = list(
        map(
            FeatureSchema().load,
            [
                dict(
                    name="taskBased",
                    type="task_based",
                    high_pass_filter_cutoff=125.0,
                    conditions=["a", "b"],
                    contrasts=[
                        dict(name="a>b", type="t", values=dict(a=1.0, b=-1.0)),
                    ],
                    setting="dualRegAndSeedCorrAndTaskBasedSetting",
                ),
                dict(
                    name="seedCorr",
                    type="seed_based_connectivity",
                    seeds=["pcc"],
                    setting="dualRegAndSeedCorrAndTaskBasedSetting",
                ),
                dict(
                    name="dualReg",
                    type="dual_regression",
                    maps=["smith09"],
                    setting="dualRegAndSeedCorrAndTaskBasedSetting",
                ),
                dict(
                    name="corrMatrix",
                    type="atlas_based_connectivity",
                    atlases=["schaefer2018"],
                    setting="fALFFAndReHoAndCorrMatrixSetting",
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
            ],
        )
    )

    spec.global_settings.update(dict(sloppy=True))

    return spec


@pytest.fixture(scope="function")
def consistency_spec(mock_spec):
    """
    Extend the mock_spec fixture to add extra file specification
    This fixture builds upon the existing mock_spec fixture, adding a new feature specifications.
    """

    # Clone the spec to avoid modifying the original mock_spec
    consistency_spec = deepcopy(mock_spec)

    new_feature = dict(
        name="corrMatrix",
        type="atlas_based_connectivity",
        atlases=["schaefer2018"],
        setting="fALFFAndReHoAndCorrMatrixSetting",
    )

    # new_settings ?
    # new_files ?

    # Load the feature
    new_feature_loaded = FeatureSchema().load(new_feature)
    consistency_spec.features.append(new_feature_loaded)

    return consistency_spec
