# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op
import json

from functools import partial
from multiprocessing import Pool

from nipype.pipeline import engine as pe
from nipype.interfaces import io as nio

from .firstlevel import init_subject_wf

from .stats import init_higherlevel_wf

from ..interface.filter import Filter

from ..utils import transpose
from .utils import (
    make_varname,
    dataSinkRegexpSubstitutions
)
from ..nodes import (
    TryNode,
    TryMapNode
)


def init_workflow(workdir, jsonfile):
    """
    initialize nipype workflow for a workdir containing a pipeline.json file.

    :param workdir: path to workdir
    :param jsonfile: path to pipeline.json
    """
    # TODO implement workflow caching
    # workflow_file = os.path.join(workdir, "workflow.pklz")

    fp = os.path.join(workdir, jsonfile)

    data = None
    with open(fp, "r") as f:
        data = json.load(f)

    name = "nipype"
    workflow = pe.Workflow(name=name, base_dir=workdir)

    images = transpose(data["images"])

    #
    # first level
    # Pool().

    result = Pool().map(
        partial(init_subject_wf, workdir=workdir, images=images, data=data),
        list(images.items())
    )
    subjects, subject_wfs, outfieldsByOutnameByScanArray = zip(*result)

    workflow.add_nodes(subject_wfs)

    # Remove duplicates from outfieldsByOutnameByScan
    outfieldsByOutnameByScan = {}
    for outfieldsByOutnameByScan_ in outfieldsByOutnameByScanArray:
        for scan, outfieldsByOutname in outfieldsByOutnameByScan_.items():
            if scan not in outfieldsByOutnameByScan:
                outfieldsByOutnameByScan[scan] = {}
            for outname, outfields in outfieldsByOutname.items():
                if outname not in outfieldsByOutnameByScan[scan]:
                    outfieldsByOutnameByScan[scan][outname] = set()
                outfieldsByOutnameByScan[scan][outname].update(outfields)

    #
    # second level
    #

    # Run second level statistics only if json file does
    # not correspond to a single subject
    # group_json = os.path.join(workdir, "pipeline.json")
    # if group_json == fp:

    metadata = data["metadata"]
    group_design = metadata["GroupDesign"]
    group_data = group_design["Data"]

    subject_sets = {
        "AllSubjects": subjects
    }
    repeat_within_subgroup_fields = group_design["RepeatWithinSubGroups"]
    for field in repeat_within_subgroup_fields:
        subject_groups = group_data[field]["SubjectGroups"]
        unique_groups = set(subject_groups.values())
        for group in unique_groups:
            subject_set_name = "Within_{}.{}".format(field, group)
            subject_set = {
                subject for subject, g in subject_groups.items() if g == group
            }
            subject_sets[subject_set_name] = subject_set

    stats_dir = os.path.join(workdir, "stats")
    for scanname, outfieldsByOutname in outfieldsByOutnameByScan.items():
        for outname, outfields in outfieldsByOutname.items():
            for subject_set_name, subject_set in subject_sets.items():
                outdir = op.join(stats_dir, scanname, outname)
                if len(subject_sets) > 1:
                    outdir = op.join(outdir, subject_set_name)
                suffix = "{}_{}".format(
                    scanname, outname
                )
                if len(subject_sets) > 1:
                    suffix += "_{}".format(
                        subject_set_name.replace(".", "_"))

                fieldnames = ["subject"]
                for outfield in outfields:
                    if outfield in ["stat", "var", "dof_file", "mask_file"]:
                        fieldnames.append(outfield)

                higherlevel_wf = init_higherlevel_wf(
                    fieldnames,
                    group_data,
                    run_mode="flame1",
                    name="%s_higherlevel" % suffix,
                )

                if higherlevel_wf is None:
                    continue

                filter = pe.Node(
                    interface=Filter(
                        numinputs=len(subjects),
                        fieldnames=fieldnames
                    ),
                    name="{}_subjects_filter".format(suffix)
                )

                for i, (subject, wf) in enumerate(zip(subjects, subject_wfs)):
                    if subject not in subject_set:
                        continue

                    outputnode = None
                    for node in wf._get_all_nodes():
                        nodename = "scan_%s.outputnode" % scanname
                        if str(node).endswith('.' + nodename):
                            outputnode = node
                            break
                    for outfield in fieldnames:
                        if outfield == "subject":
                            continue
                        workflow.connect([
                            (outputnode, filter, [
                                (make_varname(outname, outfield),
                                    "{}{}".format(outfield, i + 1))
                            ]),
                        ])
                    workflow.connect([
                        (outputnode, filter, [
                            ("keep", "is_enabled%i" % (i + 1))
                        ]),
                    ])
                    setattr(filter.inputs, "subject{}".format(i + 1), subject)

                for outfield in fieldnames:
                    workflow.connect([
                        (filter, higherlevel_wf, [
                            (outfield, "inputnode.{}".format(outfield))
                        ]),
                    ])

                ds_stats = TryMapNode(
                    nio.DataSink(
                        infields=["cope", "varcope", "zstat", "dof"],
                        regexp_substitutions=dataSinkRegexpSubstitutions,
                        base_directory=outdir,
                        parameterization=False,
                        force_run=True),
                    iterfield=["container", "cope", "varcope", "zstat", "dof"],
                    name="ds_%s_stats" % suffix,
                    run_without_submitting=True
                )

                ds_mask = TryNode(
                    nio.DataSink(
                        infields=["mask"],
                        base_directory=outdir,
                        regexp_substitutions=dataSinkRegexpSubstitutions,
                        parameterization=False,
                        force_run=True),
                    name="ds_%s_mask" % suffix,
                    run_without_submitting=True
                )

                workflow.connect([
                    (higherlevel_wf, ds_stats, [
                        ("outputnode.contrast_names", "container")
                    ]),
                    (higherlevel_wf, ds_stats, [
                        ("outputnode.copes", "cope")
                    ]),
                    (higherlevel_wf, ds_stats, [
                        ("outputnode.varcopes", "varcope")
                    ]),
                    (higherlevel_wf, ds_stats, [
                        ("outputnode.zstats", "zstat")
                    ]),
                    (higherlevel_wf, ds_stats, [
                        ("outputnode.dof_files", "dof")
                    ]),
                    (higherlevel_wf, ds_mask, [
                        ("outputnode.mask_file", "mask")
                    ])
                ])

    return workflow
