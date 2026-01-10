# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import os
import shutil
import tarfile
import tempfile

# from halfpipe.logging.context import Context, setup as setup_logging
from math import inf
from pathlib import Path
from random import choices, normalvariate, seed
from typing import Iterator
from uuid import uuid5
from zipfile import ZipFile

import nibabel as nib
import pandas as pd
import pytest
from nilearn.image import new_img_like

from halfpipe import __version__
from halfpipe.collect.bold import collect_bold_files
from halfpipe.fixes.workflows import IdentifiableWorkflow
from halfpipe.ingest.bids import BidsDatabase
from halfpipe.ingest.database import Database
from halfpipe.model.file.base import File
from halfpipe.model.file.schema import FileSchema
from halfpipe.model.spec import Spec, SpecSchema, save_spec
from halfpipe.resource import get as get_resource
from halfpipe.utils.image import nvol
from halfpipe.workflows.convert import convert_all
from halfpipe.workflows.factory import FactoryContext
from halfpipe.workflows.features.factory import FeatureFactory
from halfpipe.workflows.fmriprep.factory import FmriprepFactory
from halfpipe.workflows.post_processing.factory import PostProcessingFactory
from halfpipe.workflows.features.factory import FeatureFactory
from halfpipe.workflows.downstream_features.factory import DownstreamFeatureFactory

from ..create_mock_bids_dataset import create_bids_data
from ..resource import setup as setup_test_resources
from .spec import TestSetting, make_bids_only_spec, make_spec


@pytest.fixture(scope="session")
def bids_data(tmp_path_factory) -> Path:
    tmp_path = tmp_path_factory.mktemp(basename="rawdata")  # renamed to match FmriprepFactory set up/get config

    os.chdir(str(tmp_path))

    setup_test_resources()
    # TODO consider renaming at source
    input_path = get_resource("bids_data.zip")

    with ZipFile(input_path) as fp:
        fp.extractall(tmp_path)

    bids_data_path = tmp_path / "rawdata"  # renamed to match FmriprepFactory set up/get config

    os.rename(tmp_path / "bids_data", bids_data_path)  # renamed to match FmriprepFactory set up/get config

    # add dataset description for bids
    json_data = {"Name": "HALFpipe test data", "BIDSVersion": "1.6.0"}
    with open(bids_data_path / "dataset_description.json", "w") as f:
        f.write(json.dumps(json_data))

    func_path = bids_data_path / "sub-1012" / "func"

    Path(func_path / "sub-1012_task-rest_events.tsv").unlink()  # this file is empty

    bold_file = func_path / "sub-1012_task-rest_bold.nii.gz"
    bold_img = nib.nifti1.load(bold_file)
    bold_data = bold_img.get_fdata()[..., :64]  # we don't need so many volumes for testing
    bold_img = new_img_like(bold_img, bold_data, copy_header=True)
    nib.loadsave.save(bold_img, bold_file)

    return bids_data_path


@pytest.fixture(scope="session")
def mock_task_events(tmp_path_factory, bids_data) -> File:
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

    return FileSchema().load(
        dict(
            datatype="func",
            suffix="events",
            extension=".tsv",
            tags=dict(task="rest"),
            path=str(events_fname),
            metadata=dict(units="seconds"),
        )
    )


@pytest.fixture(scope="session")
def atlas_harvard_oxford(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    tmp_path = tmp_path_factory.mktemp(basename="pcc_mask")

    os.chdir(str(tmp_path))
    setup_test_resources()

    inputtarpath = get_resource("HarvardOxford.tgz")

    with tarfile.open(inputtarpath) as fp:
        fp.extractall(tmp_path)

    maps = {
        m: (tmp_path / "data" / "atlases" / "HarvardOxford" / f"HarvardOxford-{m}.nii.gz")
        for m in ("cort-prob-1mm", "cort-prob-2mm", "sub-prob-1mm", "sub-prob-2mm")
    }
    return maps


@pytest.fixture(scope="session")
def pcc_mask(tmp_path_factory: pytest.TempPathFactory, atlas_harvard_oxford: dict[str, Path]) -> Path:
    tmp_path = tmp_path_factory.mktemp(basename="pcc_mask")

    os.chdir(str(tmp_path))

    atlas_img = nib.nifti1.load(atlas_harvard_oxford["cort-prob-2mm"])
    atlas = atlas_img.get_fdata()

    pcc_mask = atlas[..., 29] > 10

    pcc_mask_img = new_img_like(atlas_img, pcc_mask, copy_header=True)

    pcc_mask_fname = Path.cwd() / "pcc.nii.gz"
    nib.loadsave.save(pcc_mask_img, pcc_mask_fname)

    return pcc_mask_fname


# TODO check this & implement tests w gradients
@pytest.fixture(scope="session")
def margulies2016_gradients(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp_path = tmp_path_factory.mktemp(basename="gradients")

    os.chdir(str(tmp_path))

    os.chdir(str(tmp_path))
    setup_test_resources()

    zip_path = get_resource("Gradients_Margulies2016.zip")
    with ZipFile(zip_path) as fp:
        fp.extractall(tmp_path)

    gradients_path = tmp_path / "Gradients_Margulies2016" / "volumes" / "volume.grad_1.MNI2mm.nii.gz"

    return gradients_path


@pytest.fixture(scope="function")
def mock_spec(bids_data: Path, mock_task_events: File, pcc_mask: Path) -> Spec:
    bids_file = FileSchema().load(
        dict(datatype="bids", path=str(bids_data)),
    )

    base_setting = dict(
        confounds_removal=["(trans|rot)_[xyz]"],
        grand_mean_scaling=dict(mean=10000.0),
        ica_aroma=True,
    )
    test_settings = [
        TestSetting(
            name="standard",
            base_setting=dict(space="standard", **base_setting),
        ),
        TestSetting(
            name="native",
            base_setting=dict(space="native", **base_setting),
        ),
    ]

    return make_spec(dataset_files=[bids_file], pcc_mask=pcc_mask, test_settings=test_settings, event_file=mock_task_events)


@pytest.fixture(scope="session")
def bids_session_test_data(request: pytest.FixtureRequest) -> Iterator[tuple[Path, Path]]:
    """
    Create a parallel-safe temporary BIDS hierarchy with optional number of sessions + workdir.

    - Accepts sessions via request.param
    - Cleans up after the test
    """
    sessions = getattr(request, "param", [])

    # Use a unique temporary directory (parallel-safe)
    base_path = Path(tempfile.mkdtemp(prefix="bids_test_"))
    bids_label = "multisession-bids"
    data_path = base_path / bids_label
    workdir_path = base_path / "workdir"
    data_path.mkdir(parents=True, exist_ok=True)
    workdir_path.mkdir(parents=True, exist_ok=True)

    # Example BIDS setup
    number_of_subjects = 3
    tasks_conditions_dict = {
        "anticipation_acq-seq": ["cue_negative", "cue_neutral", "img_negative", "img_neutral"],
        "workingmemory_acq-seq": ["active_change", "active_nochange", "passive"],
        "restingstate-mb3": [],
    }

    create_bids_data(
        data_path,
        number_of_subjects=number_of_subjects,
        tasks_conditions_dict=tasks_conditions_dict,
        field_maps=True,
        sessions=sessions,
    )

    bids_file = FileSchema().load(dict(datatype="bids", path=str(data_path)))

    mock_spec = make_bids_only_spec(dataset_files=[bids_file])
    preproc_setting = {
        "space": "standard",
        "name": "preproc",
        "filters": [{"type": "tag", "action": "include", "entity": "task", "values": ["workingmemory"]}],
        "output_image": True,
    }
    mock_spec.settings.append(preproc_setting)
    save_spec(mock_spec, workdir=workdir_path)

    # Yield paths to the test
    yield data_path, workdir_path

    # Cleanup after the test
    shutil.rmtree(base_path)


@pytest.fixture(scope="function")
def mock_ctx(
    tmp_path,
    bids_data,  # returns path to bids_data, fixture defined in conftest
    mock_spec,  # what exactly is in here?
):
    """Create a mock FactoryContext based on the mock_spec fixture."""
    # init database
    database = Database(mock_spec, bids_database_dir=bids_data)
    # init bids database
    bids_database = BidsDatabase(database)
    bold_file_paths_dict = collect_bold_files(mock_spec, database)
    convert_all(database, bids_database, bold_file_paths_dict)

    # from workflows.base
    uuid = uuid5(mock_spec.uuid, database.sha1 + __version__)
    workflow = IdentifiableWorkflow(name="nipype", base_dir=tmp_path, uuid=uuid)
    workflow.config["execution"].update(
        dict(
            create_report=True,  # each node writes a text file with inputs and outputs
            crashdump_dir=workflow.base_dir,
            crashfile_format="txt",
            hash_method="timestamp",
            poll_sleep_duration=0.5,
            use_relative_paths=False,
            check_version=False,
        )
    )

    return FactoryContext(tmp_path, mock_spec, database, bids_database, workflow)


# Note these fixtures return the factory objects post-setup bc the following factory setup is dependent on it
# TODO refactor such that each of these fixtures only has to init the factory & rest is internal
@pytest.fixture(scope="function")
def mock_fmriprep_factory_tuple(
    bids_data,
    mock_spec,
    mock_ctx,
):
    """Outputs a tuple of FmriprepFactory along with the setup outputs for the following factory."""
    database = Database(mock_spec, bids_database_dir=bids_data)
    bold_file_paths_dict = collect_bold_files(mock_spec, database)

    fmriprep_factory = FmriprepFactory(mock_ctx)
    fmriprep_bold_file_paths, processing_groups = fmriprep_factory.setup(
        Path(str(bids_data)[:-8]), set(bold_file_paths_dict.keys())
    )

    # filter out skipped files
    bold_file_paths_dict = {
        bold_file_path: associated_file_paths
        for bold_file_path, associated_file_paths in bold_file_paths_dict.items()
        if bold_file_path in fmriprep_bold_file_paths
    }
    return fmriprep_factory, bold_file_paths_dict, processing_groups


@pytest.fixture(scope="function")
def mock_post_processing_factory(
    mock_ctx,
    mock_fmriprep_factory_tuple,
):
    mock_fmriprep_factory = mock_fmriprep_factory_tuple[0]
    bold_file_paths_dict = mock_fmriprep_factory_tuple[1]
    processing_groups = mock_fmriprep_factory_tuple[2]

    post_processing_factory = PostProcessingFactory(mock_ctx, mock_fmriprep_factory)
    post_processing_factory.setup(bold_file_paths_dict, processing_groups=processing_groups)
    return post_processing_factory


@pytest.fixture(scope="function")
def mock_feature_factory(
    mock_ctx,
    mock_fmriprep_factory_tuple,
    mock_post_processing_factory,
):
    mock_fmriprep_factory = mock_fmriprep_factory_tuple[0]
    bold_file_paths_dict = mock_fmriprep_factory_tuple[1]
    processing_groups = mock_fmriprep_factory_tuple[2]

    feature_factory = FeatureFactory(mock_ctx, mock_fmriprep_factory, mock_post_processing_factory)
    feature_factory.setup(bold_file_paths_dict, processing_groups=processing_groups)
    return feature_factory

@pytest.fixture(scope="function")
def mock_downstream_feature_factory(
    mock_ctx,
    mock_feature_factory,
    ):

    downstream_feature_factory = DownstreamFeatureFactory(mock_ctx, mock_feature_factory)
    downstream_feature_factory.setup()
    return downstream_feature_factory
