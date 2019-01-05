# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from os import path as op

from functools import partial
from multiprocessing import Pool

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import io as nio

from .firstlevel import init_subject_wf

from .stats import init_higherlevel_wf

from .qualitycheck import get_qualitycheck_exclude

from ..utils import transpose


def init_workflow(workdir):
    """
    initialize nipype workflow for a workdir containing a pipeline.json file.

    :param workdir: path to workdir

    """
    workflow_file = op.join(workdir, "workflow.pklz")

    fp = op.join(workdir, "pipeline.json")

    data = None
    with open(fp, "r") as f:
        data = json.load(f)

    name = "nipype"
    workflow = pe.Workflow(name=name, base_dir=workdir)

    images = transpose(data["images"])

    #
    # first level
    #

    result = Pool().map(
        partial(init_subject_wf, workdir=workdir, images=images, data=data),
        list(images.items())
    )
    subjects, subject_wfs, outnameslists = zip(*result)
    workflow.add_nodes(subject_wfs)

    #
    # second level
    #

    outnamessets = {}
    for outnameslist in outnameslists:
        for k, v in outnameslist.items():
            if k not in outnamessets:
                outnamessets[k] = set()
            outnamessets[k].update(v)

    exclude = get_qualitycheck_exclude(workdir)

    metadata = data["metadata"]
    subject_groups = None
    if "SubjectGroups" in metadata:
        subject_groups = metadata["SubjectGroups"]
    group_contrasts = None
    if "GroupContrasts" in metadata:
        group_contrasts = metadata["GroupContrasts"]
    covariates = None
    if "Covariates" in metadata:
        covariates = metadata["Covariates"]

    stats_dir = op.join(workdir, "stats")

    for task, outnamesset in outnamessets.items():
        for outname in outnamesset:
            higherlevel_wf, contrast_names = init_higherlevel_wf(run_mode="flame1",
                                                                 name="%s_%s_higherlevel" % (task, outname),
                                                                 subjects=subjects, covariates=covariates,
                                                                 subject_groups=subject_groups,
                                                                 group_contrasts=group_contrasts)

            mergecopes = pe.Node(
                interface=niu.Merge(len(subject_wfs)),
                name="%s_%s_mergecopes" % (task, outname))
            mergevarcopes = pe.Node(
                interface=niu.Merge(len(subject_wfs)),
                name="%s_%s_mergevarcopes" % (task, outname))
            mergemasks = pe.Node(
                interface=niu.Merge(len(subject_wfs)),
                name="%s_%s_mergemasks" % (task, outname))
            mergedoffiles = pe.Node(
                interface=niu.Merge(len(subject_wfs)),
                name="%s_%s_mergedoffiles" % (task, outname))

            for i, (subject, wf) in enumerate(zip(subjects, subject_wfs)):
                excludethis = False
                if subject in exclude:
                    if task in exclude[subject]:
                        excludethis = exclude[subject][task]
                if not excludethis:
                    nodename = "task-%s.outputnode" % task
                    outputnode = [
                        node for node in wf._graph.nodes()
                        if str(node).endswith('.' + nodename)
                    ]
                    if len(outputnode) > 0:
                        outputnode = outputnode[0]
                        workflow.connect(outputnode, "%s_cope" % outname, mergecopes, "in%i" % (i + 1))
                        workflow.connect(outputnode, "%s_varcope" % outname, mergevarcopes, "in%i" % (i + 1))
                        workflow.connect(outputnode, "%s_dof_file" % outname, mergedoffiles, "in%i" % (i + 1))
                        workflow.connect(outputnode, "%s_mask_file" % outname, mergemasks, "in%i" % (i + 1))

            ds_stats = pe.MapNode(
                nio.DataSink(
                    infields=["cope", "varcope", "zstat", "dof"],
                    base_directory=op.join(stats_dir, task, outname),
                    regexp_substitutions=[(r"(/.+)/\w+.nii.gz", r"\1.nii.gz")],
                    parameterization=False),
                iterfield=["container", "cope", "varcope", "zstat", "dof"],
                name="ds_%s_%s_stats" % (task, outname), run_without_submitting=True)
            ds_stats.inputs.container = contrast_names

            ds_mask = pe.Node(
                nio.DataSink(
                    base_directory=op.join(stats_dir, task),
                    container=outname,
                    parameterization=False),
                name="ds_%s_%s_mask" % (task, outname), run_without_submitting=True)

            workflow.connect([
                (mergecopes, higherlevel_wf, [
                    ("out", "inputnode.copes")
                ]),
                (mergevarcopes, higherlevel_wf, [
                    ("out", "inputnode.varcopes")
                ]),
                (mergemasks, higherlevel_wf, [
                    ("out", "inputnode.mask_files")
                ]),
                (mergedoffiles, higherlevel_wf, [
                    ("out", "inputnode.dof_files")
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
