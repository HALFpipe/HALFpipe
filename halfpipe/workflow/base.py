# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from uuid import uuid5
import logging

from nipype.pipeline import engine as pe

from .factory import FactoryContext
from .fmriprep import FmriprepFactory
from .setting import SettingFactory
from .feature import FeatureFactory
from .model import ModelFactory

from .execgraph import init_execgraph
from .memory import MemoryCalculator
from ..io import Database, BidsDatabase, cacheobj, uncacheobj
from ..model import loadspec


def init_workflow(workdir):
    """
    initialize nipype workflow

    :param spec
    """

    logger = logging.getLogger("halfpipe")

    spec = loadspec(workdir=workdir)
    database = Database(spec)
    uuid = uuid5(spec.uuid, database.sha1)

    workflow = uncacheobj(workdir, "workflow", uuid)
    if workflow is not None:
        return init_execgraph(workdir, workflow)

    # create parent workflow
    workflow = pe.Workflow(name="nipype", base_dir=workdir)
    workflow.uuid = uuid
    uuidstr = str(uuid)[:8]
    logger.info(f"Initializing new workflow: {uuidstr}")
    workflow.config["execution"].update(
        {
            "crashdump_dir": workflow.base_dir,
            "poll_sleep_duration": 0.1,
            "use_relative_paths": False,
            "check_version": False,
        }
    )

    # create factories
    bidsdatabase = BidsDatabase(database)
    memcalc = MemoryCalculator(database)
    ctx = FactoryContext(workdir, spec, bidsdatabase, workflow, memcalc)
    fmriprep_factory = FmriprepFactory(ctx)
    setting_factory = SettingFactory(ctx, fmriprep_factory)
    feature_factory = FeatureFactory(ctx, setting_factory)
    model_factory = ModelFactory(ctx, feature_factory)

    # setup preprocessing
    boldfilepaths = setting_factory.sourcefiles | feature_factory.sourcefiles
    fmriprep_factory.setup(workdir, boldfilepaths)
    setting_factory.setup()
    feature_factory.setup()
    model_factory.setup()

    logger.info(f"Finished workflow: {uuidstr}")

    cacheobj(workdir, "workflow", workflow)
    return init_execgraph(workdir, workflow)
