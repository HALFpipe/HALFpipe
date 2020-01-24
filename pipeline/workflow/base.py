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
# from .stats_wg import init_higherlevel_wg_wf

from ..interface.filter import Filter

from ..utils import transpose
from .utils import make_varname


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

                ds_stats = pe.MapNode(
                    nio.DataSink(
                        infields=["cope", "varcope", "zstat", "dof"],
                        base_directory=outdir,
                        parameterization=False),
                    iterfield=["container", "cope", "varcope", "zstat", "dof"],
                    name="ds_%s_stats" % suffix,
                    run_without_submitting=True
                )

                ds_mask = pe.Node(
                    nio.DataSink(
                        base_directory=os.path.join(stats_dir, scanname),
                        container=outname,
                        parameterization=False),
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

# 
# def init_stat_only_workflow(workdir, jsonfile):
#     """
#     initialize workflow for already preprocessed data, grabbing data from the intermediates folder
# 
#     :param workdir: path to workdir
#     :param jsonfile: path to pipeline.json
#     """
#     workflow_file = os.path.join(workdir, "workflow.pklz")
# 
#     fp = os.path.join(workdir, jsonfile)
# 
#     data = None
#     with open(fp, "r") as f:
#         data = json.load(f)
# 
#     name = "nipype"
#     workflow = pe.Workflow(name=name, base_dir=workdir)
# 
#     images = transpose(data["images"])
# 
#     #
#     # first level
#     #
# 
#     result = Pool().map(
#         partial(init_subject_wf, workdir=workdir, images=images, data=data),
#         list(images.items())
#     )
#     subjects, subject_wfs, outnameslists = zip(*result)
# 
#     #
#     # second level
#     #
# 
#     # Run second level statistics only if json file does not correspond to a single subject
#     group_json = os.path.join(workdir, "pipeline.json")
#     if group_json == fp:
# 
#         # Remove duplicates from outnameslists
#         outnamessets = {}
#         for outnameslist in outnameslists:
#             for k, v in outnameslist.items():
#                 if k not in outnamessets:
#                     outnamessets[k] = set()
#                 outnamessets[k].update(v)
# 
#         exclude = get_qualitycheck_exclude(workdir)
#         metadata = data["metadata"]
#         subject_groups = None
#         if "SubjectGroups" in metadata:
#             subject_groups = metadata["SubjectGroups"]
#         group_contrasts = None
#         if "GroupContrasts" in metadata:
#             group_contrasts = metadata["GroupContrasts"]
#         covariates = None
#         if "Covariates" in metadata:
#             covariates = metadata["Covariates"]
# 
#         stats_dir = os.path.join(workdir, "stats")
# 
#         for task, outnamesset in outnamessets.items():
#             for outname in outnamesset:
#                 higherlevel_wf, contrast_names = init_higherlevel_wf(run_mode="flame1",
#                                                                      name="%s_%s_higherlevel" % (task, outname),
#                                                                      subjects=subjects, covariates=covariates,
#                                                                      subject_groups=subject_groups,
#                                                                      group_contrasts=group_contrasts,
#                                                                      outname=outname, workdir=workdir, task=task)
#                 mergecopes = pe.Node(
#                     interface=niu.Merge(len(subject_wfs)),
#                     name="%s_%s_mergecopes" % (task, outname))
#                 mergevarcopes = pe.Node(
#                     interface=niu.Merge(len(subject_wfs)),
#                     name="%s_%s_mergevarcopes" % (task, outname))
#                 mergemasks = pe.Node(
#                     interface=niu.Merge(len(subject_wfs)),
#                     name="%s_%s_mergemasks" % (task, outname))
#                 mergedoffiles = pe.Node(
#                     interface=niu.Merge(len(subject_wfs)),
#                     name="%s_%s_mergedoffiles" % (task, outname))
#                 mergezstats = pe.Node(
#                     interface=niu.Merge(len(subject_wfs)),
#                     name="%s_%s_mergezstats" % (task, outname))
# 
#                 for i, (subject, wf) in enumerate(zip(subjects, subject_wfs)):
#                     excludethis = False
#                     if subject in exclude:
#                         if task in exclude[subject]:
#                             excludethis = exclude[subject][task]
#                     if not excludethis:
#                         nodename = "scan_%s.outputnode" % task
#                         outputnode = [
#                             node for node in wf._graph.nodes()
#                             if str(node).endswith('.' + nodename)
#                         ]
#                         if len(outputnode) > 0:
#                             outputnode = outputnode[0]
#                             if outname in ["reho", "alff", "falff"]:
#                                 dg_node = pe.Node(
#                                     nio.DataGrabber(infields=['subject_id', 'scan_name', 'outname'],
#                                                     outfields=['cope', 'zstat', 'mask_file']),
#                                     name=f'dg_{subject}_{task}_{outname}'
#                                 )
#                                 dg_node.inputs.base_directory = workdir + '/intermediates/'
#                                 dg_node.inputs.template = '*'
#                                 dg_node.inputs.sort_filelist = True
#                                 dg_node.inputs.template_args = {
#                                     'cope': [['subject_id', 'scan_name', 'outname']],
#                                     'zstat': [['subject_id', 'scan_name', 'outname']],
#                                     'mask_file': [['subject_id', 'scan_name']]
#                                 }
#                                 dg_node.inputs.field_template = {
#                                     'cope': '%s/%s/%s_img.nii.gz',
#                                     'zstat': '%s/%s/%s_zstat.nii.gz',
#                                     'mask_file': '%s/%s/mask.nii.gz',
#                                 }
#                                 dg_node.inputs.subject_id = subject
#                                 dg_node.inputs.scan_name = task
#                                 dg_node.inputs.outname = outname
#                                 workflow.connect(dg_node, "cope", mergecopes, "in%i" % (i + 1))
#                                 workflow.connect(dg_node, "zstat", mergezstats, "in%i" % (i + 1))
#                                 workflow.connect(dg_node, "mask_file", mergemasks, "in%i" % (i + 1))
#                             else:
#                                 dg_node = pe.Node(
#                                     nio.DataGrabber(infields=['subject_id', 'scan_name', 'outname'],
#                                                     outfields=['cope', 'mask_file', 'varcope', 'dof_file']),
#                                     name=f'dg_{subject}_{task}_{outname}'
#                                 )
#                                 dg_node.inputs.base_directory = workdir + '/intermediates/'
#                                 dg_node.inputs.template = '*'
#                                 dg_node.inputs.sort_filelist = True
#                                 dg_node.inputs.template_args = {
#                                     'cope': [['subject_id', 'scan_name', 'outname']],
#                                     'mask_file': [['subject_id', 'scan_name']],
#                                     'varcope': [['subject_id', 'scan_name', 'outname']],
#                                     'dof_file': [['subject_id', 'scan_name']]
#                                 }
#                                 dg_node.inputs.field_template = {
#                                     'cope': '%s/%s/%s_cope.nii.gz',
#                                     'mask_file': '%s/%s/mask.nii.gz',
#                                     'varcope': '%s/%s/%s_varcope.nii.gz',
#                                     'dof_file': '%s/%s/dof',
# 
#                                 }
#                                 dg_node.inputs.subject_id = subject
#                                 dg_node.inputs.scan_name = task
#                                 dg_node.inputs.outname = outname
#                                 workflow.connect(dg_node, "cope", mergecopes, "in%i" % (i + 1))
#                                 workflow.connect(dg_node, "mask_file", mergemasks, "in%i" % (i + 1))
#                                 workflow.connect(dg_node, "varcope", mergevarcopes, "in%i" % (i + 1))
#                                 workflow.connect(dg_node, "dof_file", mergedoffiles, "in%i" % (i + 1))
# 
#                 ds_stats = pe.MapNode(
#                     nio.DataSink(
#                         infields=["cope", "varcope", "zstat", "dof"],
#                         base_directory=os.path.join(stats_dir, task, outname),
#                         regexp_substitutions=[(r"(/.+)/\w+.nii.gz", r"\1.nii.gz")],
#                         parameterization=False),
#                     iterfield=["container", "cope", "varcope", "zstat", "dof"],
#                     name="ds_%s_%s_stats" % (task, outname), run_without_submitting=True)
#                 ds_stats.inputs.container = contrast_names
# 
#                 ds_mask = pe.Node(
#                     nio.DataSink(
#                         base_directory=os.path.join(stats_dir, task),
#                         container=outname,
#                         parameterization=False),
#                     name="ds_%s_%s_mask" % (task, outname), run_without_submitting=True)
# 
#                 if outname in ["reho", "alff", "falff"]:
#                     workflow.connect([
#                         (mergecopes, higherlevel_wf, [
#                             ("out", "inputnode.copes")
#                         ]),
#                         (mergezstats, higherlevel_wf, [
#                             ("out", "inputnode.zstats")
#                         ]),
#                         (mergemasks, higherlevel_wf, [
#                             ("out", "inputnode.mask_files")
#                         ]),
#                     ])
# 
#                     workflow.connect([
#                         (higherlevel_wf, ds_stats, [
#                             ("outputnode.copes", "cope")
#                         ]),
#                         (higherlevel_wf, ds_stats, [
#                             ("outputnode.varcopes", "varcope")
#                         ]),
#                         (higherlevel_wf, ds_stats, [
#                             ("outputnode.zstats", "zstat")
#                         ]),
#                         (higherlevel_wf, ds_stats, [
#                             ("outputnode.dof_files", "dof")
#                         ]),
#                         (higherlevel_wf, ds_mask, [
#                             ("outputnode.mask_file", "mask")
#                         ])
#                     ])
# 
#                 else:
#                     workflow.connect([
#                         (mergecopes, higherlevel_wf, [
#                             ("out", "inputnode.copes")
#                         ]),
#                         (mergemasks, higherlevel_wf, [
#                             ("out", "inputnode.mask_files")
#                         ]),
#                     ])
# 
#                     workflow.connect([
#                         (mergevarcopes, higherlevel_wf, [
#                             ("out", "inputnode.varcopes")
#                         ]),
#                         (mergedoffiles, higherlevel_wf, [
#                             ("out", "inputnode.dof_files")
#                         ])
#                     ])
# 
#                     workflow.connect([
#                         (higherlevel_wf, ds_stats, [
#                             ("outputnode.copes", "cope")
#                         ]),
#                         (higherlevel_wf, ds_stats, [
#                             ("outputnode.varcopes", "varcope")
#                         ]),
#                         (higherlevel_wf, ds_stats, [
#                             ("outputnode.zstats", "zstat")
#                         ]),
#                         (higherlevel_wf, ds_stats, [
#                             ("outputnode.dof_files", "dof")
#                         ]),
#                         (higherlevel_wf, ds_mask, [
#                             ("outputnode.mask_file", "mask")
#                         ])
#                     ])
# 
#     return workflow