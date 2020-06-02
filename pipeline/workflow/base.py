# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from uuid import uuid5
import pickle

from calamities.pattern import get_entities_in_path
from ..database import Database
from ..spec import loadspec, study_entities, bold_entities
from ..utils import cacheobj, uncacheobj
from ..io import get_repetition_time, PreprocessedImgCopyOutResultHook
from .utils import make_resultdict_datasink

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from .fmriprepwrapper import (
    init_anat_preproc_wf,
    init_func_preproc_wf,
    connect_func_wf_attrs_from_anat_preproc_wf,
    get_fmaps,
)
from .firstlevel import init_firstlevel_analysis_wf, connect_firstlevel_analysis_extra_args
from .higherlevel import init_higherlevel_analysis_wf
from .filt import (
    init_bold_filt_wf,
    make_variant_bold_filt_wf_name,
    connect_filt_wf_attrs_from_anat_preproc_wf,
    connect_filt_wf_attrs_from_func_preproc_wf,
)
from .report import (
    init_anat_report_wf,
    init_func_report_wf,
    connect_anat_report_wf_attrs_from_anat_preproc_wf,
    connect_func_report_wf_attrs_from_anat_preproc_wf,
    connect_func_report_wf_attrs_from_func_preproc_wf,
    connect_func_report_wf_attrs_from_filt_wf,
)
from .memory import memcalc_from_database

analysisoutattr = "outputnode.resultdicts"


class Cache:
    def __init__(self):
        self._cache = {}

    def get(self, func, argtuples=None):
        if argtuples is None:
            key = repr(func)
        else:
            key = (repr(func), tuple(argtuples))
        if key not in self._cache:
            kwargs = {}
            if argtuples is not None:
                kwargs = dict(list(argtuples))
            obj = func(**kwargs)
            self._cache[key] = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        return pickle.loads(self._cache[key])


def init_workflow(workdir, freesurfer=False, no_compose_transforms=False):
    """
    initialize nipype workflow

    :param spec
    """

    logger = logging.getLogger("pipeline")

    spec = loadspec(workdir=workdir)
    database = Database(files=spec.files)
    uuid = uuid5(spec.uuid, database.sha1())

    workflow = uncacheobj(workdir, "workflow", uuid)
    if workflow is not None:
        return workflow

    # create workflow
    workflow = pe.Workflow(name="nipype", base_dir=workdir)
    workflow.uuid = uuid
    uuidstr = str(uuid)[:8]
    logger.info(f"New workflow: {uuidstr}")
    workflow.config["execution"].update(
        {
            "crashdump_dir": workflow.base_dir,
            "poll_sleep_duration": 0.1,
            "use_relative_paths": False,
            "check_version": False,
        }
    )

    # helpers
    memcalc = memcalc_from_database(database)
    cache = Cache()

    subjectlevelworkflow = pe.Workflow(name=f"subjectlevel")
    workflow.add_nodes([subjectlevelworkflow])

    firstlevel_analyses = [analysis for analysis in spec.analyses if analysis.level == "first"]
    firstlevel_analysis_tagdicts = [
        analysis.tags.get_tagdict(study_entities) for analysis in firstlevel_analyses
    ]

    subjectlevel_analyses = [
        analysis
        for analysis in spec.analyses
        if analysis.level == "higher" and analysis.across != "subject"
    ]

    grouplevel_analyses = [
        analysis
        for analysis in spec.analyses
        if analysis.level == "higher" and analysis.across == "subject"
    ]

    analysisendpoints = {analysis.name: [] for analysis in spec.analyses}

    subjects = database.get_tagval_set("subject")
    for subject in subjects:
        subjectmetadata = {"subject": subject}

        subjectfiles = database.get(subject=subject)

        subjectworkflow = pe.Workflow(name=f"subject_{subject}")
        subjectlevelworkflow.add_nodes([subjectworkflow])

        t1wfiles = database.filter(subjectfiles, datatype="anat", suffix="T1w")
        nt1wfiles = len(t1wfiles)
        if nt1wfiles == 0:
            logger.warn(f'Found {nt1wfiles} T1w files for subject "{subject}", skipping')
            continue
        t1wfile = t1wfiles.pop()
        if nt1wfiles > 1:
            logger.warn(f'Found {nt1wfiles} T1w files for subject "{subject}", using "{t1wfile}"')
        anat_preproc_wf = cache.get(
            init_anat_preproc_wf,
            argtuples=[
                ("workdir", workdir),
                ("no_compose_transforms", no_compose_transforms),
                ("freesurfer", freesurfer),
            ],
        )
        anat_preproc_wf.get_node("inputnode").inputs.t1w = t1wfile
        anat_preproc_wf.get_node("inputnode").inputs.metadata = subjectmetadata
        subjectworkflow.add_nodes([anat_preproc_wf])

        anat_report_wf = cache.get(
            init_anat_report_wf, argtuples=[("workdir", workdir), ("memcalc", memcalc)]
        )
        anat_report_wf.get_node("inputnode").inputs.metadata = subjectmetadata
        connect_anat_report_wf_attrs_from_anat_preproc_wf(
            subjectworkflow, anat_preproc_wf, anat_report_wf,
        )

        if len(firstlevel_analyses) == 0:
            continue

        boldfiles = database.filter(subjectfiles, datatype="func", suffix="bold")
        subjectanalysisendpoints = {analysis.name: [] for analysis in spec.analyses}
        for boldfile in boldfiles:
            # make name
            boldfilemetadata = subjectmetadata.copy()
            has_direction = True
            if database.get_tagval(boldfile, "direction") is not None:
                tmplstr = database.get_tmplstr(boldfile)
                entities_in_path = get_entities_in_path(tmplstr)
                has_direction = "direction" in entities_in_path
            name = "bold"
            for entity in study_entities:
                value = database.get_tagval(boldfile, entity)
                if value is not None and (entity != "direction" or has_direction):
                    name += "_"
                    name += f"{entity}_{value}"
                    boldfilemetadata[entity] = value
            # workflow
            boldfileworkflow = pe.Workflow(name=name)
            fmap_type, fmaps, fmapmetadata = get_fmaps(boldfile, database)
            boldfilemetadata.update(fmapmetadata)

            repetition_time = database.get_tagval(boldfile, "repetition_time")
            if repetition_time is None:
                repetition_time = get_repetition_time(boldfile)
            assert (
                repetition_time > 0.01
            ), f'Repetition time value "{repetition_time}" is too low for file "{boldfile}"'
            boldfilemetadata["RepetitionTime"] = repetition_time

            func_preproc_wf = cache.get(
                init_func_preproc_wf,
                argtuples=[("workdir", workdir), ("fmap_type", fmap_type), ("memcalc", memcalc)],
            )
            boldfileworkflow.add_nodes([func_preproc_wf])
            func_preproc_inputnode = func_preproc_wf.get_node("inputnode")
            func_preproc_inputnode.inputs.bold_file = boldfile
            func_preproc_inputnode.inputs.fmaps = fmaps
            func_preproc_inputnode.inputs.metadata = boldfilemetadata
            connect_func_wf_attrs_from_anat_preproc_wf(
                subjectworkflow,
                anat_preproc_wf,
                boldfileworkflow,
                in_nodename=f"{func_preproc_wf.name}.inputnode",
            )
            func_report_wf = None
            for analysis, tagdict in zip(firstlevel_analyses, firstlevel_analysis_tagdicts):
                if not database.matches(boldfile, **tagdict):
                    continue
                # get analysis workflow
                analysisworkflow, boldfilevariants = cache.get(
                    init_firstlevel_analysis_wf,
                    argtuples=[("analysis", analysis), ("memcalc", memcalc)],
                )
                # workflow input variants
                bold_filt_wf = None
                for attrnames, variant in boldfilevariants:
                    name = make_variant_bold_filt_wf_name(variant)
                    variant_bold_filt_wf = boldfileworkflow.get_node(name)
                    if variant_bold_filt_wf is None:
                        variant_bold_filt_wf = cache.get(
                            init_bold_filt_wf,
                            argtuples=[("variant", variant), ("memcalc", memcalc)],
                        )
                        boldfileworkflow.add_nodes([variant_bold_filt_wf])
                        variant_bold_filt_wf.get_node(
                            "inputnode"
                        ).inputs.metadata = boldfilemetadata
                        connect_filt_wf_attrs_from_anat_preproc_wf(
                            subjectworkflow,
                            anat_preproc_wf,
                            boldfileworkflow,
                            in_nodename=f"{variant_bold_filt_wf.name}.inputnode",
                        )
                        connect_filt_wf_attrs_from_func_preproc_wf(
                            boldfileworkflow, func_preproc_wf, variant_bold_filt_wf
                        )
                    if bold_filt_wf is None:  # use first variant bold_filt_wf
                        bold_filt_wf = variant_bold_filt_wf
                    for i, attrname in enumerate(attrnames):
                        boldfileworkflow.connect(
                            variant_bold_filt_wf,
                            f"outputnode.out{i+1}",
                            analysisworkflow,
                            f"inputnode.{attrname}",
                        )
                boldfileworkflow.connect(
                    bold_filt_wf, "outputnode.mask_file", analysisworkflow, "inputnode.mask_file",
                )
                connect_firstlevel_analysis_extra_args(
                    analysisworkflow, analysis, database, boldfile
                )
                # use first variant to create func_report_wf
                if func_report_wf is None:
                    func_report_wf = cache.get(
                        init_func_report_wf, argtuples=[("workdir", workdir), ("memcalc", memcalc)]
                    )
                    func_report_wf.get_node("inputnode").inputs.metadata = boldfilemetadata
                    connect_func_report_wf_attrs_from_filt_wf(
                        boldfileworkflow, bold_filt_wf, func_report_wf
                    )
                    connect_func_report_wf_attrs_from_func_preproc_wf(
                        boldfileworkflow, func_preproc_wf, func_report_wf
                    )
                    connect_func_report_wf_attrs_from_anat_preproc_wf(
                        subjectworkflow,
                        anat_preproc_wf,
                        boldfileworkflow,
                        in_nodename=f"{func_report_wf.name}.inputnode",
                    )
                boldfileworkflow.connect(
                    func_report_wf, "outputnode.metadata", analysisworkflow, "inputnode.metadata",
                )
                # sink outputs
                endpoint = (boldfileworkflow, f"{analysisworkflow.name}.{analysisoutattr}")
                make_resultdict_datasink(
                    boldfileworkflow,
                    workdir,
                    (analysisworkflow, analysisoutattr),
                    name=f"{analysisworkflow.name}_resultdictdatasink",
                )
                if analysis.type == "atlas_based_connectivity" or analysis.type == "image_output":
                    pass
                else:  # FIXME don't fail with zero copes
                    subjectanalysisendpoints[analysis.name].append(endpoint)
        # subjectlevel aggregate
        for analysis in subjectlevel_analyses:
            endpoints = []
            for inputanalysisname in analysis.input:
                endpoints.extend(subjectanalysisendpoints[inputanalysisname])
            collectinputs = pe.Node(
                niu.Merge(numinputs=len(endpoints)), name=f"collectinputs_{analysis.name}",
            )
            for i, endpoint in enumerate(endpoints):
                subjectworkflow.connect(*endpoint, collectinputs, f"in{i+1}")
            analysisworkflow = cache.get(
                init_higherlevel_analysis_wf,
                argtuples=[("analysis", analysis), ("memcalc", memcalc)],
            )
            subjectworkflow.connect(collectinputs, "out", analysisworkflow, "inputnode.indicts")
            endpoint = (subjectworkflow, f"{analysisworkflow.name}.{analysisoutattr}")
            subjectanalysisendpoints[analysis.name].append(endpoint)
            make_resultdict_datasink(
                subjectworkflow,
                workdir,
                (analysisworkflow, analysisoutattr),
                name=f"{analysisworkflow.name}_resultdictdatasink",
            )
        for analysisname, endpoints in subjectanalysisendpoints.items():
            for endpoint in endpoints:
                node, attr = endpoint
                attr = f"{node.name}.{attr}"
                if node is not subjectworkflow:
                    attr = f"{subjectworkflow.name}.{attr}"
                analysisendpoints[analysisname].append((subjectlevelworkflow, attr))

    grouplevelworkflow = pe.Workflow(name=f"grouplevel")

    for analysis in grouplevel_analyses:
        endpoints = []
        for inputanalysisname in analysis.input:
            endpoints.extend(analysisendpoints[inputanalysisname])
        if len(endpoints) == 0:
            continue
        collectinputs = pe.Node(
            niu.Merge(numinputs=len(endpoints)), name=f"collectinputs_{analysis.name}",
        )
        grouplevelworkflow.add_nodes([collectinputs])
        for i, endpoint in enumerate(endpoints):
            workflow.connect(*endpoint, grouplevelworkflow, f"{collectinputs.name}.in{i+1}")
        analysisworkflow = cache.get(
            init_higherlevel_analysis_wf, argtuples=[("analysis", analysis), ("memcalc", memcalc)],
        )
        grouplevelworkflow.connect(collectinputs, "out", analysisworkflow, "inputnode.indicts")
        endpoint = (grouplevelworkflow, f"{analysisworkflow.name}.{analysisoutattr}")
        analysisendpoints[analysis.name].append(endpoint)
        make_resultdict_datasink(
            grouplevelworkflow,
            workdir,
            (analysisworkflow, analysisoutattr),
            name=f"{analysisworkflow.name}_resultdictdatasink",
        )

    cacheobj(workdir, "workflow", workflow)

    boldfiledicts = []
    for boldfile in database.get(datatype="func", suffix="bold"):
        tags_obj = database.get_tags(boldfile)
        boldfiledict = tags_obj.get_tagdict(bold_entities)
        if "direction" in boldfiledict:
            tmplstr = database.get_tmplstr(boldfile)
            entities_in_path = get_entities_in_path(tmplstr)
            if "direction" not in entities_in_path:
                del boldfiledict["direction"]
        boldfiledicts.append(boldfiledict)

    PreprocessedImgCopyOutResultHook(workdir).init_dictlistfile(boldfiledicts)

    return workflow
