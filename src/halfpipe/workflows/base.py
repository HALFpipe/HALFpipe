# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from typing import Optional
from uuid import uuid5

from .. import __version__
from ..fixes.workflows import IdentifiableWorkflow
from ..ingest.bids import BidsDatabase
from ..ingest.database import Database
from ..logging import logger
from ..model.spec import Spec, load_spec
from ..utils.cache import cache_obj, uncache_obj
from ..utils.copy import deepcopyfactory
from .constants import Constants
from .convert import convert_all
from .factory import FactoryContext
from .features import FeatureFactory
from .fmriprep import FmriprepFactory
from .memory import MemoryCalculator
from .mriqc import MriqcFactory
from .post_processing import PostProcessingFactory
from .stats import StatsFactory


def init_workflow(workdir: Path, spec: Optional[Spec] = None) -> IdentifiableWorkflow:
    """
    initialize nipype workflow
    :param workdir
    :param spec
    """
    from ..collect.bold import collect_bold_files

    if not spec:
        spec = load_spec(workdir=workdir)

    assert spec is not None, "A spec file could not be loaded"
    logger.info("Initializing file database")
    database = Database(spec)
    # uuid depends on the spec file, the files found and the version of the program
    uuid = uuid5(spec.uuid, database.sha1 + __version__)

    workflow = uncache_obj(workdir, ".workflow", uuid, display_str="workflow")
    if workflow is not None:
        assert isinstance(workflow, IdentifiableWorkflow)
        return workflow

    # init classes that use the database
    bids_database = BidsDatabase(database)

    # create parent workflow

    uuidstr = str(uuid)[:8]
    logger.info(f"Initializing new workflow {uuidstr}")

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

    if len(spec.features) == 0 and not any(setting.get("output_image") is True for setting in spec.settings):
        raise RuntimeError("Nothing to do. Please specify features to calculate and/or select to output a preprocessed image")

    # create factories

    ctx = FactoryContext(workdir, spec, database, bids_database, workflow)
    fmriprep_factory = FmriprepFactory(ctx)
    post_processing_factory = PostProcessingFactory(ctx, fmriprep_factory)
    feature_factory = FeatureFactory(ctx, post_processing_factory)
    stats_factory = StatsFactory(ctx, feature_factory)

    bold_file_paths_dict: dict[str, list[str]] = collect_bold_files(database, post_processing_factory, feature_factory)

    # write out

    convert_all(database, bids_database, bold_file_paths_dict)

    for bold_file_path in bold_file_paths_dict.keys():
        bids_path = bids_database.to_bids(bold_file_path)
        if bids_path is None:
            continue  # File is not used because it is a duplicate

        subject = database.tagval(bold_file_path, "sub")
        assert isinstance(subject, str)
        bids_subject = bids_database.get_tag_value(bids_path, "subject")
        assert isinstance(bids_subject, str)

        workflow.bids_to_sub_id_map[bids_subject] = subject

    bids_dir = Path(workdir) / "rawdata"
    bids_database.write(bids_dir)

    # setup preprocessing

    if spec.global_settings.get("run_mriqc") is True:
        mriqc_factory = MriqcFactory(ctx)
        mriqc_factory.setup(
            workdir,
            list(bold_file_paths_dict.keys()),
        )

    if spec.global_settings.get("run_fmriprep") is True:
        fmriprep_bold_file_paths = fmriprep_factory.setup(
            workdir,
            set(bold_file_paths_dict.keys()),
        )

        # filter out skipped files
        bold_file_paths_dict = {
            bold_file_path: associated_file_paths
            for bold_file_path, associated_file_paths in bold_file_paths_dict.items()
            if bold_file_path in fmriprep_bold_file_paths
        }

        if spec.global_settings.get("run_halfpipe") is True:
            post_processing_factory.setup(bold_file_paths_dict)
            feature_factory.setup(bold_file_paths_dict)
            stats_factory.setup()

    # patch workflow
    config_factory = deepcopyfactory(workflow.config)
    min_gb = MemoryCalculator.default().min_gb

    for node in workflow._get_all_nodes():
        node.config = config_factory()
        if node.name in ["split"]:
            node.config["execution"]["hash_method"] = "content"

        node.overwrite = None
        node.run_without_submitting = False  # run all nodes in multiproc

        if node._mem_gb < min_gb:  # enforce minimum
            node._mem_gb = min_gb

    logger.info(f"Finished workflow {uuidstr}")
    cache_obj(workdir, ".workflow", workflow)

    return workflow
