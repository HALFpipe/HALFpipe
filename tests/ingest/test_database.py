import re
from datetime import datetime
from pathlib import Path

import bids

from halfpipe.ingest.database import Database
from halfpipe.model.file.bids import BidsFileSchema
from halfpipe.model.spec import Spec

from ..create_mock_bids_dataset import create_bids_data


def test_bids_database_dir(tmp_path: Path) -> None:
    tasks_conditions_dict = {
        "anticipation_acq-seq": ["cue_negative", "cue_neutral", "img_negative", "img_neutral"],
        "workingmemory_acq-seq": ["active_change", "active_nochange", "passive"],
        "restingstate_acq-mb3": [],
    }
    data_path = tmp_path / "ds002785"
    create_bids_data(data_path, number_of_subjects=3, tasks_conditions_dict=tasks_conditions_dict, field_maps=True)

    indexer = bids.BIDSLayoutIndexer(
        validate=True,
        ignore=[re.compile("^(?!/sub-0001)")],
    )

    bids_database_dir = tmp_path / "bids_database"
    bids_layout = bids.BIDSLayout(
        root=data_path,
        indexer=indexer,
        validate=True,
        database_path=bids_database_dir,
        reset_database=True,
    )

    for bids_file in bids_layout.get():
        assert bids_file.tags["subject"].value == "0001"

    spec = Spec(timestamp=datetime.now(), files=[BidsFileSchema().load({"datatype": "bids", "path": str(data_path)})])

    database = Database(spec, bids_database_dir=bids_database_dir)
    assert database.tagvalset("sub") == {"0001"}
