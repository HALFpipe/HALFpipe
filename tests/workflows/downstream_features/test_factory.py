import os
import pytest
import numpy as np

import datetime

from halfpipe.model.feature import Feature #, GradientsFeatureSchema, FeatureSchema
from halfpipe.workflows.memory import MemoryCalculator

from halfpipe.workflows.downstream_features.gradients import init_gradients_wf
from halfpipe.utils.nipype import run_workflow

from halfpipe.ingest.bids import BidsDatabase
from halfpipe.ingest.database import Database

from halfpipe.workflows.factory import FactoryContext

# TODO
# test I/O through features/nodes/workflow
# how do you define a feature to then pass elsewhere?

def test_gradients_factory(tmp_path):
    """Test to check connection of gradients wf with previous atlas based connectivity wf."""

    # TODO fix/change
    workdir = tmp_path
    bids_database_dir = tmp_path

    timestamp = datetime.datetime.now()
    files = []
    features = []
    downstream_features = []

    # TODO how/when are specs generated?
    # object is created as post_load using whatever data is passed to load
    spec = Spec(
        timestamp, 
        files,
        features = features,
        downstream_features = downstream_features,
        )
    
    database = Database(
        spec, 
        bids_database_dir=bids_database_dir
        )
    bids_database = BidsDatabase(database)

    # from workflows.base
    workflow = IdentifiableWorkflow(name=Constants.workflow_directory, base_dir=workdir, uuid=uuid)
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
        workdir, 
        spec, 
        database, 
        bids_database, 
        workflow
        )
    
    fmriprep_factory = FmriprepFactory(ctx)
    post_processing_factory = PostProcessingFactory(ctx, fmriprep_factory)
    feature_factory = FeatureFactory(ctx, fmriprep_factory, post_processing_factory)
    downstream_feature_factory = DownstreamFeatureFactory(ctx, fmriprep_factory)
