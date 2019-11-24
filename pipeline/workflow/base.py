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

from .qualitycheck import get_qualitycheck_exclude

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

    print("PRINT:" + str(subjects))
    print("PRINT:" + str(subject_wfs))
    # print("PRINT:" + str(type(subject_wfs)))
    # print("PRINT:" + str(type(subject_wfs[0])))

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

            # Remove duplicates from outnameslists
            outnamessets = {}
            for outnameslist in outnameslists:
                for k, v in outnameslist.items():
                    if k not in outnamessets:
                        outnamessets[k] = set()
                    outnamessets[k].update(v)

            print("PRINT: lists: " + str(outnameslists))
            print("PRINT: sets: " + str(outnamessets))

            exclude = get_qualitycheck_exclude(workdir)

            models = {}

            bg_name = "between_group"
            if "GroupContrasts" in metadata:
                between_group = {bg_name: {"GroupContrasts": metadata["GroupContrasts"],
                                           "SubjectGroups": metadata["SubjectGroups"],
                                           "Covariates": metadata["Covariates"]}}
                models.update(between_group)

            if "WithinGroup" in metadata:
                models.update(metadata["WithinGroup"])

            print("PRINT: models: "+str(models))

            stats_dir = os.path.join(workdir, "stats")

            for model in models:

                for task, outnamesset in outnamessets.items():
                    for outname in outnamesset:

                        name = "%s_%s_%s_higherlevel" % (model, task, outname)
                        covariates = models[model]["Covariates"]
                        subject_groups = models[model]["SubjectGroups"]

                        print("PRINT: "+name+' '+outname)

                        if model == bg_name:
                            print("PRINT: between group model")
                            wfs = subject_wfs
                            group_contrasts = models[model]["GroupContrasts"]
                            higherlevel_wf, contrast_names = init_higherlevel_wf(run_mode="flame1",
                                                                             name=name,
                                                                             subjects=subjects, covariates=covariates,
                                                                             subject_groups=subject_groups,
                                                                             group_contrasts=group_contrasts,
                                                                             outname=outname, workdir=workdir, task=task)

                        else:
                            print("PRINT: within group model\n"+model)
                            # Selection of specified subjects
                            subjects_wg = list(subject_groups)
                            subject_wfs_wg = []
                            for (subject, wf) in zip(subjects, subject_wfs):
                                if subject in subjects_wg:
                                    subject_wfs_wg.append(wf)
                            wfs = subject_wfs_wg

                            print("PRINT:" + str(subjects_wg))
                            print("PRINT:" + str(subject_wfs_wg))
                            #print("PRINT:" + str(type(subject_wfs_wg[0])))

                            continuous_variable = models[model]["ContinuousVariable"]
                            higherlevel_wf, contrast_names = init_higherlevel_wg_wf(run_mode="flame1",
                                                                             name=name,
                                                                             subjects=subjects_wg, covariates=covariates,
                                                                             subject_groups=subject_groups,
                                                                             continuous_variable=continuous_variable,
                                                                             outname=outname, workdir=workdir, task=task)

                        detailed_name = "%s_%s_%s" % (model, task, outname)

                        mergecopes = pe.Node(
                            interface=niu.Merge(len(wfs)),
                            name="%s_mergecopes" % detailed_name)
                        mergevarcopes = pe.Node(
                            interface=niu.Merge(len(wfs)),
                            name="%s_mergevarcopes" % detailed_name)
                        mergemasks = pe.Node(
                            interface=niu.Merge(len(wfs)),
                            name="%s_mergemasks" % detailed_name)
                        mergedoffiles = pe.Node(
                            interface=niu.Merge(len(wfs)),
                            name="%s_mergedoffiles" % detailed_name)
                        mergezstats = pe.Node(
                            interface=niu.Merge(len(wfs)),
                            name="%s_mergezstats" % detailed_name)

                        for i, (subject, wf) in enumerate(zip(subjects, wfs)):
                            excludethis = False
                            if subject in exclude:
                                if task in exclude[subject]:
                                    excludethis = exclude[subject][task]
                            if not excludethis:
                                nodename = "model_%s_task_%s.outputnode" % (model, task)
                                outputnode = [
                                    node for node in wf._graph.nodes()
                                    if str(node).endswith('.' + nodename)
                                ]
                                if len(outputnode) > 0:
                                    outputnode = outputnode[0]
                                    if outname in ["reho", "alff", "falff"]:
                                        workflow.connect(outputnode, "%s_cope" % outname, mergecopes, "in%i" % (i + 1))
                                        workflow.connect(outputnode, "%s_zstat" % outname, mergezstats, "in%i" % (i + 1))
                                        workflow.connect(outputnode, "%s_mask_file" % outname, mergemasks, "in%i" % (i + 1))
                                    else:
                                        workflow.connect(outputnode, "%s_cope" % outname, mergecopes, "in%i" % (i + 1))
                                        workflow.connect(outputnode, "%s_mask_file" % outname, mergemasks, "in%i" % (i + 1))
                                        workflow.connect(outputnode, "%s_varcope" % outname, mergevarcopes, "in%i" % (i + 1))
                                        workflow.connect(outputnode, "%s_dof_file" % outname, mergedoffiles, "in%i" % (i + 1))

                        ds_stats = pe.MapNode(
                            nio.DataSink(
                                infields=["cope", "varcope", "zstat", "dof"],
                                base_directory=os.path.join(stats_dir, model, task, outname),
                                regexp_substitutions=[(r"(/.+)/\w+.nii.gz", r"\1.nii.gz")],
                                parameterization=False),
                            iterfield=["container", "cope", "varcope", "zstat", "dof"],
                            name="ds_%s_stats" % detailed_name, run_without_submitting=True)
                        ds_stats.inputs.container = contrast_names

                        ds_mask = pe.Node(
                            nio.DataSink(
                                base_directory=os.path.join(stats_dir, model, task),
                                container=outname,
                                parameterization=False),
                            name="ds_%s_mask" % detailed_name, run_without_submitting=True)

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
