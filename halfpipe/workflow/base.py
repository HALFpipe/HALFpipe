# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from uuid import uuid5
import logging
from pathlib import Path

from nipype.pipeline import engine as pe
from fmriprep import config

from .factory import FactoryContext
from .mriqc import MriqcFactory
from .fmriprep import FmriprepFactory
from .setting import SettingFactory
from .feature import FeatureFactory
from .model import ModelFactory

from .memory import MemoryCalculator
from .constants import constants
from ..io import Database, BidsDatabase, cacheobj, uncacheobj
from ..model import loadspec
from ..utils import deepcopyfactory, nvol


def init_workflow(workdir):
    """
    initialize nipype workflow

    :param spec
    """

    logger = logging.getLogger("halfpipe")

    spec = loadspec(workdir=workdir)
    assert spec is not None, "A spec file could not be loaded"
    logger.info("Initializing file database")
    database = Database(spec)
    uuid = uuid5(spec.uuid, database.sha1)

    workflow = uncacheobj(workdir, "workflow", uuid)
    if workflow is not None:
        return workflow

    # create parent workflow
    workflow = pe.Workflow(name=constants.workflowdir, base_dir=workdir)
    workflow.uuid = uuid
    uuidstr = str(uuid)[:8]
    logger.info(f"Initializing new workflow: {uuidstr}")
    workflow.config["execution"].update(
        {
            "crashdump_dir": workflow.base_dir,
            "crashfile_format": "txt",
            "poll_sleep_duration": 0.75,
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

    # find bold files

    boldfilepaths = setting_factory.sourcefiles | feature_factory.sourcefiles

    # filter

    associated_filepaths_dict = dict()

    for boldfilepath in boldfilepaths:
        sub = database.tagval(boldfilepath, "sub")
        filters = dict(sub=sub)  # enforce same subject

        t1ws = database.associations(boldfilepath, datatype="anat", **filters)

        if t1ws is None:  # remove bold files without T1w
            continue

        associated_filepaths = [boldfilepath, *t1ws]

        fmaps = database.associations(boldfilepath, datatype="fmap", **filters)
        if fmaps is not None:
            associated_filepaths.extend(fmaps)

        associated_filepaths_dict[boldfilepath] = associated_filepaths

    boldfilepaths = [b for b in boldfilepaths if b in associated_filepaths_dict]

    tmpbidsdatabase = BidsDatabase(database)
    bidsdict = dict()
    for boldfilepath in boldfilepaths:
        tmpbidsdatabase.put(boldfilepath)
        bidspath = tmpbidsdatabase.tobids(boldfilepath)
        assert bidspath is not None
        if bidspath not in bidsdict:
            bidsdict[bidspath] = set()
        bidsdict[bidspath].add(boldfilepath)

    for boldfilepathset in bidsdict.values():
        if len(boldfilepathset) == 1:
            continue

        # remove duplicates by scan length
        # this is a heuristic based on the idea that duplicate scans may be
        # scans that were cancelled or had technical difficulties and therefore
        # had to be restarted
        nvoldict = {
            boldfilepath: nvol(boldfilepath) for boldfilepath in boldfilepathset
        }
        maxnvol = max(nvoldict.values())
        selected = set(k for k, v in nvoldict.items() if v == maxnvol)

        if len(selected) > 1:
            # if the heuristic above doesn't work, we just choose the alphabetically
            # last one
            last = sorted(selected)[-1]
            selected = set([last])

        (selectedboldfilepath,) = selected

        message_strs = [
            f'Found {len(boldfilepathset)-1:d} file with identical tags to {selectedboldfilepath}":'
        ]
        for boldfilepath in boldfilepathset:
            if boldfilepath != selectedboldfilepath:
                message_strs.append(f'Excluding file "{boldfilepath}"')
        if nvoldict[boldfilepath] < maxnvol:
            message_strs.append("Decision criterion was: Image with the longest duration")
        else:
            message_strs.append("Decision criterion was: Last image when sorting alphabetically")
        logger.warning("\n".join(message_strs))

        for boldfilepath in boldfilepathset:
            if boldfilepath != selectedboldfilepath:
                del associated_filepaths_dict[boldfilepath]

    # write out

    for associated_filepaths in associated_filepaths_dict.values():
        for filepath in associated_filepaths:
            bidsdatabase.put(filepath)

    boldfilepaths = [b for b in boldfilepaths if b in associated_filepaths_dict]

    bids_dir = Path(workdir) / "rawdata"
    bidsdatabase.write(bids_dir)

    # setup preprocessing
    if spec.global_settings.get("run_mriqc") is True:
        mriqc_factory = MriqcFactory(ctx)
        mriqc_factory.setup(workdir, boldfilepaths)
    if spec.global_settings.get("run_fmriprep") is True:
        fmriprep_factory.setup(workdir, boldfilepaths)

        if spec.global_settings.get("run_halfpipe") is True:
            setting_factory.setup(associated_filepaths_dict)
            feature_factory.setup(associated_filepaths_dict)
            model_factory.setup()

    config_factory = deepcopyfactory(workflow.config)
    for node in workflow._get_all_nodes():
        node.config = config_factory()
        if node.name in ["split"]:
            node.config["execution"]["hash_method"] = "content"
        node.overwrite = None
        if node.name in ["bold_to_std_transform", "bold_to_t1w_transform", "bold_transform"]:
            node._mem_gb = memcalc.volume_std_gb * 50 * config.nipype.omp_nthreads

    logger.info(f"Finished workflow: {uuidstr}")

    cacheobj(workdir, "workflow", workflow)
    return workflow
