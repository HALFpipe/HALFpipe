import os
import pytest
import numpy as np

from uuid import uuid5
from pathlib import Path
from halfpipe import __version__

from halfpipe.fixes.workflows import IdentifiableWorkflow

from halfpipe.model.feature import Feature #, GradientsFeatureSchema, FeatureSchema
from halfpipe.model.spec import Spec

from halfpipe.workflows.constants import Constants
from halfpipe.workflows.convert import convert_all

from halfpipe.ingest.bids import BidsDatabase
from halfpipe.ingest.database import Database

from halfpipe.collect.bold import collect_bold_files

from halfpipe.workflows.factory import FactoryContext
from halfpipe.workflows.fmriprep.factory import FmriprepFactory

# TODO
# test I/O through features/nodes/workflow
# how do you define a feature to then pass elsewhere?

# TODO move to conftest?
@pytest.fixture(scope="function")
def fmriprep_factory(
    tmp_path, 
    bids_data, # returns path to bids_data, fixture defined in conftest
    mock_spec, # what exactly is in here?
    ):
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

    # create a context
    ctx = FactoryContext(
        tmp_path, 
        mock_spec, 
        database, 
        bids_database, 
        workflow
        )
    
    return FmriprepFactory(ctx)

def test_collect_bold_files(tmp_path, bids_data, mock_spec):
    """ Check if collected bold files is empty."""
    database = Database(mock_spec, bids_database_dir=bids_data)

    bold_file_paths_dict = collect_bold_files(mock_spec, database)
    assert len(bold_file_paths_dict) > 0

def test_init(fmriprep_factory):
    """ Check fmriprep_factory fixture creation."""
    assert isinstance(fmriprep_factory, FmriprepFactory)

def test_setup(bids_data, mock_spec, fmriprep_factory):
    """ Check that setup works with test data."""
    database = Database(mock_spec, bids_database_dir=bids_data)
    bold_file_paths_dict = collect_bold_files(mock_spec, database)

    fmriprep_factory.setup(Path(str(bids_data)[:-8]), set(bold_file_paths_dict.keys()))
    
