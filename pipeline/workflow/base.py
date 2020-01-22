# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import json

from functools import partial
from multiprocessing import Pool

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import io as nio

from .firstlevel import init_subject_wf

from .stats import init_higherlevel_wf
from .stats_wg import init_higherlevel_wg_wf

from ..interface.filter import Filter

from ..utils import transpose

def init_workflow(workdir, jsonfile):
    """
    initialize nipype workflow for a workdir containing a pipeline.json file.

    :param workdir: path to workdir
    :param jsonfile: path to pipeline.json
    """
    workflow_file = os.path.join(workdir, "workflow.pklz")

    fp = os.path.join(workdir, jsonfile)

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

    # Run second level statistics only if json file does not correspond to a single subject
    group_json = os.path.join(workdir, "pipeline.json")
    if group_json == fp:

        metadata = data["metadata"]

        # Only run if SubjectGroups is present in json file
        if "SubjectGroups" in metadata:
            subject_groups = metadata["SubjectGroups"]
        group_contrasts = None
        if "GroupContrasts" in metadata:
            group_contrasts = metadata["GroupContrasts"]
        covariates = None
        if "Covariates" in metadata:
            covariates = metadata["Covariates"]

        stats_dir = os.path.join(workdir, "stats")

        for task, outnamesset in outnamessets.items():
            for outname in outnamesset:
                
                higherlevel_wf, contrast_names = init_higherlevel_wf(run_mode="flame1",
                                                                     name="%s_%s_higherlevel" % (task, outname),
                                                                     subjects=subjects, covariates=covariates,
                                                                     subject_groups=subject_groups,
                                                                     group_contrasts=group_contrasts,
                                                                     outname=outname, workdir=workdir, task=task)
                filtercopes = pe.Node(
                    interface=Filter(len(subjects)),
                    name="%s_%s_filtercopes" % (task, outname))
                filtercopes = pe.Node(
                    interface=Filter(len(subjects)),
                    name="%s_%s_filtercopes" % (task, outname))
                filtervarcopes = pe.Node(
                    interface=Filter(len(subjects)),
                    name="%s_%s_filtervarcopes" % (task, outname))
                filtermasks = pe.Node(
                    interface=Filter(len(subjects)),
                    name="%s_%s_filtermasks" % (task, outname))
                filterdoffiles = pe.Node(
                    interface=Filter(len(subjects)),
                    name="%s_%s_filterdoffiles" % (task, outname))
                filterzstats = pe.Node(
                    interface=Filter(len(subjects)),
                    name="%s_%s_filterzstats" % (task, outname))

                for i, (subject, wf) in enumerate(zip(subjects, included_wfs)):
                    nodename = "task_%s.outputnode" % task
                    outputnode = [node for node in wf._get_all_nodes() 
                                  if str(node).endswith('.' + nodename)]
                    if len(outputnode) > 0:
                        outputnode = outputnode[0]
                        workflow.connect([
                            (outputnode, filtercopes, [
                                ("%s_cope" % outname, "in%i" % (i + 1)),
                                ("keep", "is_enabled%i" % (i + 1))
                            ]),
                            (outputnode, filtermasks, [
                                ("%s_mask_file" % outname, "in%i" % (i + 1)),
                                ("keep", "is_enabled%i" % (i + 1))
                            ])
                        ])
                        import pdb; pdb.set_trace()
                        workflow.connect(outputnode, "%s_zstat" % outname, filterzstats, "in%i" % (i + 1))
                        workflow.connect(outputnode, "%s_mask_file" % outname, filtermasks, "in%i" % (i + 1))
                    else:
                        workflow.connect(outputnode, "%s_cope" % outname, filtercopes, "in%i" % (i + 1))
                        workflow.connect(outputnode, "%s_mask_file" % outname, filtermasks, "in%i" % (i + 1))
                        workflow.connect(outputnode, "%s_varcope" % outname, filtervarcopes, "in%i" % (i + 1))
                        workflow.connect(outputnode, "%s_dof_file" % outname, filterdoffiles, "in%i" % (i + 1))

                ds_stats = pe.MapNode(
                    nio.DataSink(
                        infields=["cope", "varcope", "zstat", "dof"],
                        base_directory=os.path.join(stats_dir, task, outname),
                        regexp_substitutions=[(r"(/.+)/\w+.nii.gz", r"\1.nii.gz")],
                        parameterization=False),
                    iterfield=["container", "cope", "varcope", "zstat", "dof"],
                    name="ds_%s_%s_stats" % (task, outname), run_without_submitting=True)
                ds_stats.inputs.container = contrast_names

                ds_mask = pe.Node(
                    nio.DataSink(
                        base_directory=os.path.join(stats_dir, task),
                        container=outname,
                        parameterization=False),
                    name="ds_%s_%s_mask" % (task, outname), run_without_submitting=True)

                if outname in ["reho", "alff", "falff"]:
                    workflow.connect([
                        (mergecopes, higherlevel_wf, [
                            ("out", "inputnode.copes")
                        ]),
                        (mergezstats, higherlevel_wf, [
                            ("out", "inputnode.zstats")
                        ]),
                        (mergemasks, higherlevel_wf, [
                            ("out", "inputnode.mask_files")
                        ]),
                    ])

                    workflow.connect([
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

                else:
                    workflow.connect([
                        (mergecopes, higherlevel_wf, [
                            ("out", "inputnode.copes")
                        ]),
                        (mergemasks, higherlevel_wf, [
                            ("out", "inputnode.mask_files")
                        ]),
                    ])

                    workflow.connect([
                        (mergevarcopes, higherlevel_wf, [
                            ("out", "inputnode.varcopes")
                        ]),
                        (mergedoffiles, higherlevel_wf, [
                            ("out", "inputnode.dof_files")
                        ])
                    ])

                    workflow.connect([
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


def init_stat_only_workflow(workdir, jsonfile):
    """
    initialize workflow for already preprocessed data, grabbing data from the intermediates folder

    :param workdir: path to workdir
    :param jsonfile: path to pipeline.json
    """
    workflow_file = os.path.join(workdir, "workflow.pklz")

    fp = os.path.join(workdir, jsonfile)

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

    #
    # second level
    #

    # Run second level statistics only if json file does not correspond to a single subject
    group_json = os.path.join(workdir, "pipeline.json")
    if group_json == fp:

        # Remove duplicates from outnameslists
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

        stats_dir = os.path.join(workdir, "stats")

        for task, outnamesset in outnamessets.items():
            for outname in outnamesset:
                higherlevel_wf, contrast_names = init_higherlevel_wf(run_mode="flame1",
                                                                     name="%s_%s_higherlevel" % (task, outname),
                                                                     subjects=subjects, covariates=covariates,
                                                                     subject_groups=subject_groups,
                                                                     group_contrasts=group_contrasts,
                                                                     outname=outname, workdir=workdir, task=task)
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
                mergezstats = pe.Node(
                    interface=niu.Merge(len(subject_wfs)),
                    name="%s_%s_mergezstats" % (task, outname))

                for i, (subject, wf) in enumerate(zip(subjects, subject_wfs)):
                    excludethis = False
                    if subject in exclude:
                        if task in exclude[subject]:
                            excludethis = exclude[subject][task]
                    if not excludethis:
                        nodename = "task_%s.outputnode" % task
                        outputnode = [
                            node for node in wf._graph.nodes()
                            if str(node).endswith('.' + nodename)
                        ]
                        if len(outputnode) > 0:
                            outputnode = outputnode[0]
                            if outname in ["reho", "alff", "falff"]:
                                dg_node = pe.Node(
                                    nio.DataGrabber(infields=['subject_id', 'task_name', 'outname'],
                                                    outfields=['cope', 'zstat', 'mask_file']),
                                    name=f'dg_{subject}_{task}_{outname}'
                                )
                                dg_node.inputs.base_directory = workdir + '/intermediates/'
                                dg_node.inputs.template = '*'
                                dg_node.inputs.sort_filelist = True
                                dg_node.inputs.template_args = {
                                    'cope': [['subject_id', 'task_name', 'outname']],
                                    'zstat': [['subject_id', 'task_name', 'outname']],
                                    'mask_file': [['subject_id', 'task_name']]
                                }
                                dg_node.inputs.field_template = {
                                    'cope': '%s/%s/%s_img.nii.gz',
                                    'zstat': '%s/%s/%s_zstat.nii.gz',
                                    'mask_file': '%s/%s/mask.nii.gz',
                                }
                                dg_node.inputs.subject_id = subject
                                dg_node.inputs.task_name = task
                                dg_node.inputs.outname = outname
                                workflow.connect(dg_node, "cope", mergecopes, "in%i" % (i + 1))
                                workflow.connect(dg_node, "zstat", mergezstats, "in%i" % (i + 1))
                                workflow.connect(dg_node, "mask_file", mergemasks, "in%i" % (i + 1))
                            else:
                                dg_node = pe.Node(
                                    nio.DataGrabber(infields=['subject_id', 'task_name', 'outname'],
                                                    outfields=['cope', 'mask_file', 'varcope', 'dof_file']),
                                    name=f'dg_{subject}_{task}_{outname}'
                                )
                                dg_node.inputs.base_directory = workdir + '/intermediates/'
                                dg_node.inputs.template = '*'
                                dg_node.inputs.sort_filelist = True
                                dg_node.inputs.template_args = {
                                    'cope': [['subject_id', 'task_name', 'outname']],
                                    'mask_file': [['subject_id', 'task_name']],
                                    'varcope': [['subject_id', 'task_name', 'outname']],
                                    'dof_file': [['subject_id', 'task_name']]
                                }
                                dg_node.inputs.field_template = {
                                    'cope': '%s/%s/%s_cope.nii.gz',
                                    'mask_file': '%s/%s/mask.nii.gz',
                                    'varcope': '%s/%s/%s_varcope.nii.gz',
                                    'dof_file': '%s/%s/dof',

                                }
                                dg_node.inputs.subject_id = subject
                                dg_node.inputs.task_name = task
                                dg_node.inputs.outname = outname
                                workflow.connect(dg_node, "cope", mergecopes, "in%i" % (i + 1))
                                workflow.connect(dg_node, "mask_file", mergemasks, "in%i" % (i + 1))
                                workflow.connect(dg_node, "varcope", mergevarcopes, "in%i" % (i + 1))
                                workflow.connect(dg_node, "dof_file", mergedoffiles, "in%i" % (i + 1))

                ds_stats = pe.MapNode(
                    nio.DataSink(
                        infields=["cope", "varcope", "zstat", "dof"],
                        base_directory=os.path.join(stats_dir, task, outname),
                        regexp_substitutions=[(r"(/.+)/\w+.nii.gz", r"\1.nii.gz")],
                        parameterization=False),
                    iterfield=["container", "cope", "varcope", "zstat", "dof"],
                    name="ds_%s_%s_stats" % (task, outname), run_without_submitting=True)
                ds_stats.inputs.container = contrast_names

                ds_mask = pe.Node(
                    nio.DataSink(
                        base_directory=os.path.join(stats_dir, task),
                        container=outname,
                        parameterization=False),
                    name="ds_%s_%s_mask" % (task, outname), run_without_submitting=True)

                if outname in ["reho", "alff", "falff"]:
                    workflow.connect([
                        (mergecopes, higherlevel_wf, [
                            ("out", "inputnode.copes")
                        ]),
                        (mergezstats, higherlevel_wf, [
                            ("out", "inputnode.zstats")
                        ]),
                        (mergemasks, higherlevel_wf, [
                            ("out", "inputnode.mask_files")
                        ]),
                    ])

                    workflow.connect([
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

                else:
                    workflow.connect([
                        (mergecopes, higherlevel_wf, [
                            ("out", "inputnode.copes")
                        ]),
                        (mergemasks, higherlevel_wf, [
                            ("out", "inputnode.mask_files")
                        ]),
                    ])

                    workflow.connect([
                        (mergevarcopes, higherlevel_wf, [
                            ("out", "inputnode.varcopes")
                        ]),
                        (mergedoffiles, higherlevel_wf, [
                            ("out", "inputnode.dof_files")
                        ])
                    ])

                    workflow.connect([
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