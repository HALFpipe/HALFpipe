# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from fmriprep.workflows.anatomical import init_anat_preproc_wf
from fmriprep.workflows.bold import init_func_preproc_wf
from fmriprep.interfaces.bids import DerivativesDataSink

from .fmriprepsettings import *

from .func import init_temporalfilter_wf, init_tsnr_wf

from .rest import init_seedconnectivity_wf, init_dualregression_wf, init_reho_wf

from .alff import create_alff

from .task import init_glm_wf

from .patch import patch_wf

from .stats import init_higherlevel_wf

from .fake import FakeBIDSLayout

from ..utils import lookup, flatten

_func_inputnode_fields = ['t1_preproc', 't1_brain', 't1_mask', 't1_seg',
                          't1_tpms', 't1_aseg', 't1_aparc',
                          't1_2_mni_forward_transform', 't1_2_mni_reverse_transform',
                          'subjects_dir', 'subject_id',
                          't1_2_fsnative_forward_transform', 't1_2_fsnative_reverse_transform']


def get_first(l):
    """
    get first element from list
    doesn't fail is input is not a list

    :param l: 

    """
    if isinstance(l, str):
        return l
    else:
        return get_first(l[0])


def init_subject_wf(item, workdir, images, data):
    """
    initialize workflow for all scans of a single subject
    :param item: input item (key/value tuple) from dictionary
    :param workdir: the working directory
    :param images: the images data structure from pipeline.json
    :param data: the entire pipeline.json
    """
    subject, value0 = item

    anat_field_names = ["T1w", "T2w", "FLAIR"]

    fmriprep_output_dir = os.path.join(workdir, "fmriprep_output")
    fmriprep_reportlets_dir = os.path.join(workdir, "fmriprep_reportlets")
    output_dir = os.path.join(workdir, "intermediates")

    subject_wf = pe.Workflow(name="sub_" + subject)

    inputnode = pe.Node(niu.IdentityInterface(
        fields=["t1w", "t2w", "flair", "subject_id", "subjects_dir"]),
        name="inputnode")

    if "T1w" not in value0:
        return subject_wf

    inputnode.inputs.t1w = value0["T1w"]

    has_func = False
    for name, value1 in value0.items():
        if name not in anat_field_names:
            has_func = True
    if not has_func:
        return subject_wf

    anat_preproc_wf = init_anat_preproc_wf(name="T1w",
                                           skull_strip_template=skull_strip_template,
                                           output_spaces=output_spaces,
                                           template=template,
                                           debug=debug,
                                           longitudinal=longitudinal,
                                           omp_nthreads=omp_nthreads,
                                           freesurfer=freesurfer,
                                           hires=hires,
                                           reportlets_dir=fmriprep_reportlets_dir,
                                           output_dir=fmriprep_output_dir,
                                           num_t1w=1)

    subject_wf.connect([
        (inputnode, anat_preproc_wf, [
            ("t1w", "inputnode.t1w"),
            ("t2w", "inputnode.t2w"),
            ("flair", "inputnode.flair"),
            ("subjects_dir", "inputnode.subjects_dir"),
            ("subject_id", "inputnode.subject_id")
        ])
    ])

    outnames = {}

    for i, (name, value1) in enumerate(value0.items()):
        if name not in anat_field_names:
            task_wf = pe.Workflow(name="task_" + name)

            inputnode = pe.Node(niu.IdentityInterface(
                fields=_func_inputnode_fields,
            ), name="inputnode")
            task_wf.add_nodes((inputnode,))

            subject_wf.connect([
                (anat_preproc_wf, task_wf, [
                    ("outputnode.%s" % f, "inputnode.%s" % f)
                    for f in _func_inputnode_fields
                ])
            ])

            metadata = data["metadata"][name]
            metadata["SmoothingFWHM"] = data["metadata"]["SmoothingFWHM"]
            metadata["TemporalFilter"] = data["metadata"]["TemporalFilter"]
            if "UseMovPar" not in metadata:
                metadata["UseMovPar"] = False

            if isinstance(value1, dict):
                #
                # multiple runs 
                #

                run_wfs = []
                outnamesset = set()

                for run, bold_file in value1.items():
                    run_wf = pe.Workflow(name="run-" + run)
                    run_wfs.append(run_wf)

                    run_inputnode = pe.Node(niu.IdentityInterface(
                        fields=_func_inputnode_fields,
                    ), name="inputnode")
                    run_wf.add_nodes((inputnode,))

                    task_wf.connect([
                        (inputnode, run_wf, [
                            (f, "inputnode.%s" % f)
                            for f in _func_inputnode_fields
                        ])
                    ])
                    run_outnames = init_func_wf(run_wf, run_inputnode, bold_file, metadata,
                                                fmriprep_reportlets_dir, fmriprep_output_dir, output_dir, run=run,
                                                subject=subject)
                    outnamesset.update(run_outnames)

                outnames[name] = outnamesset
                outputnode = pe.Node(niu.IdentityInterface(
                    fields=sum([["%s_cope" % outname,
                                 "%s_varcope" % outname, "%s_dof_file" % outname]
                                for outname in outnames[name]], [])),
                    name="outputnode"
                )

                for outname in outnames[name]:
                    mergecopes = pe.Node(
                        interface=niu.Merge(len(run_wfs)),
                        name="%s_mergecopes" % outname)
                    mergevarcopes = pe.Node(
                        interface=niu.Merge(len(run_wfs)),
                        name="%s_mergevarcopes" % outname)
                    mergedoffiles = pe.Node(
                        interface=niu.Merge(len(run_wfs)),
                        name="%s_mergedoffiles" % outname)

                    for i, wf in run_wfs:
                        task_wf.connect(wf, "outputnode.%s_cope" % outname, mergecopes, "in%i" % (i + 1))
                        task_wf.connect(wf, "outputnode.%s_varcope" % outname, mergevarcopes, "in%i" % (i + 1))
                        task_wf.connect(wf, "outputnode.%s_dof_file" % outname, mergedoffiles, "in%i" % (i + 1))

                    # aggregate stats from multiple runs in fixed-effects
                    # model
                    fe_wf, _ = init_higherlevel_wf(run_mode="fe",
                                                   name="%s_fe" % outname)

                    task_wf.connect([
                        (mergecopes, fe_wf, [
                            ("out", "inputnode.copes")
                        ]),
                        (mergevarcopes, fe_wf, [
                            ("out", "inputnode.varcopes")
                        ]),
                        (mergedoffiles, fe_wf, [
                            ("out", "inputnode.dof_files")
                        ]),

                        (fe_wf, outputnode, [
                            (("outputnode.copes", get_first), "%s_cope" % outname),
                            (("outputnode.varcopes", get_first), "%s_varcope" % outname),
                            (("outputnode.dof_files", get_first), "%s_dof_file" % outname)
                        ])
                    ])
            else:
                outnames[name] = init_func_wf(task_wf, inputnode, value1, metadata,
                                              fmriprep_reportlets_dir, fmriprep_output_dir, output_dir, subject=subject)

    subject_wf = patch_wf(subject_wf,
                          images, output_dir, fmriprep_reportlets_dir, fmriprep_output_dir)

    return subject, subject_wf, outnames


def init_func_wf(wf, inputnode, bold_file, metadata,
                 fmriprep_reportlets_dir, fmriprep_output_dir, output_dir, subject, run=None):
    """Initialize workflow for single functional scan

    :param wf: 
    :param inputnode:
    :param bold_file: 
    :param metadata:
    :param fmriprep_reportlets_dir: 
    :param fmriprep_output_dir:
    :param output_dir: 
    :param subject: 
    :param run:  (Default value = None)

    """
    while isinstance(bold_file, dict):
        bold_file = next(iter(bold_file.values()))

    layout = FakeBIDSLayout(bold_file, metadata)

    func_preproc_wf = init_func_preproc_wf(
        bold_file=bold_file,
        layout=layout,
        ignore=ignore,
        reportlets_dir=fmriprep_reportlets_dir,
        output_dir=fmriprep_output_dir,
        freesurfer=freesurfer,
        use_bbr=use_bbr,
        t2s_coreg=t2s_coreg,
        bold2t1w_dof=bold2t1w_dof,
        output_spaces=output_spaces,
        template=template,
        medial_surface_nan=medial_surface_nan,
        cifti_output=cifti_output,
        omp_nthreads=omp_nthreads,
        low_mem=low_mem,
        fmap_bspline=fmap_bspline,
        fmap_demean=fmap_demean,
        use_syn=use_syn,
        force_syn=force_syn,
        debug=debug,
        template_out_grid=template_out_grid,
        use_aroma=use_aroma,
        aroma_melodic_dim=aroma_melodic_dim,
        ignore_aroma_err=ignore_aroma_err)

    for node in func_preproc_wf._get_all_nodes():
        if type(node._interface) is fsl.SUSAN:
            node._interface.inputs.fwhm = float(metadata["SmoothingFWHM"])

    repetition_time = metadata["RepetitionTime"]

    temporalfilter_wf = init_temporalfilter_wf(
        metadata["TemporalFilter"],
        repetition_time
    )

    maskpreproc = pe.Node(
        interface=fsl.ApplyMask(),
        name="mask_preproc"
    )

    ds_preproc = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            source_file=bold_file,
            suffix="preproc"),
        name="ds_preproc", run_without_submitting=True)

    tsnr_wf = init_tsnr_wf()
    ds_tsnr = pe.Node(
        DerivativesDataSink(
            base_directory=fmriprep_reportlets_dir,
            source_file=bold_file,
            suffix="tsnr"),
        name="ds_tsnr", run_without_submitting=True)

    wf.connect([
        (inputnode, func_preproc_wf, [
            (f, "inputnode.%s" % f)
            for f in _func_inputnode_fields
        ]),
        (func_preproc_wf, temporalfilter_wf, [
            ("outputnode.nonaggr_denoised_file", "inputnode.bold_file")
        ]),
        (temporalfilter_wf, maskpreproc, [
            ("outputnode.filtered_file", "in_file")
        ]),
        (func_preproc_wf, maskpreproc, [
            ("outputnode.bold_mask_mni", "mask_file")
        ]),
        (maskpreproc, ds_preproc, [
            ("out_file", "in_file")
        ]),
        (temporalfilter_wf, tsnr_wf, [
            ("outputnode.filtered_file", "inputnode.bold_file")
        ]),
        (tsnr_wf, ds_tsnr, [
            ("outputnode.report_file", "in_file")
        ])
    ])

    conditions = None
    if "Conditions" in metadata:
        conditions = lookup(metadata["Conditions"],
                            subject_id=subject, run_id=run)

    wfbywf = {}
    outnamesbywf = {}

    #
    # first level models
    #

    def create_ds(wf, firstlevel_wf, outnames,
                  func_preproc_wf, temporalfilter_wf,
                  bold_file, output_dir, name="firstlevel"):
        """Create data sink for functional first level workflow
        (e.g., GLM or seed connectivity etc.)

        :param wf: param firstlevel_wf:
        :param outnames: param func_preproc_wf:
        :param temporalfilter_wf: param bold_file:
        :param output_dir: param name:  (Default value = "firstlevel")
        :param firstlevel_wf: 
        :param func_preproc_wf: 
        :param bold_file: 
        :param name:  (Default value = "firstlevel")

        """
        if name not in ["reho", "alff"]:
            ds_dof_file = pe.Node(
                DerivativesDataSink(
                    base_directory=output_dir,
                    source_file=bold_file,
                    suffix="dof"),
                name="ds_%s_dof_file" % name, run_without_submitting=True)

            wf.connect([
                (func_preproc_wf, firstlevel_wf, [
                    ("outputnode.bold_mask_mni", "inputnode.mask_file"),
                    ("bold_hmc_wf.outputnode.movpar_file", "inputnode.confounds_file")
                ]),
                (temporalfilter_wf, firstlevel_wf, [
                    ("outputnode.filtered_file", "inputnode.bold_file")
                ]),
                (firstlevel_wf, ds_dof_file, [
                    ("outputnode.dof_file", "in_file")
                ])
            ])

        else:
            wf.connect([
                (func_preproc_wf, firstlevel_wf, [
                    ("outputnode.bold_mask_mni", "inputnode.mask_file"),
                    ("bold_hmc_wf.outputnode.movpar_file", "inputnode.confounds_file")
                ]),
                (temporalfilter_wf, firstlevel_wf, [
                    ("outputnode.filtered_file", "inputnode.bold_file")
                ]),
            ])

        if name not in ["reho", "alff"]:
            for outname in outnames:
                ds_cope = pe.Node(
                    DerivativesDataSink(
                        base_directory=output_dir,
                        source_file=bold_file,
                        suffix="%s_cope" % outname),
                    name="ds_%s_%s_cope" % (name, outname), run_without_submitting=True)
                ds_varcope = pe.Node(
                    DerivativesDataSink(
                        base_directory=output_dir,
                        source_file=bold_file,
                        suffix="%s_varcope" % outname),
                    name="ds_%s_%s_varcope" % (name, outname), run_without_submitting=True)
                ds_zstat = pe.Node(
                    DerivativesDataSink(
                        base_directory=output_dir,
                        source_file=bold_file,
                        suffix="%s_zstat" % outname),
                    name="ds_%s_%s_zstat" % (name, outname), run_without_submitting=True)

                wf.connect([
                    (firstlevel_wf, ds_cope, [
                        ("outputnode.%s_cope" % outname, "in_file")
                    ]),
                    (firstlevel_wf, ds_varcope, [
                        ("outputnode.%s_varcope" % outname, "in_file")
                    ]),
                    (firstlevel_wf, ds_zstat, [
                        ("outputnode.%s_zstat" % outname, "in_file")
                    ]),
                ])

    if not (conditions is None or len(conditions) == 0):
        contrasts = metadata["Contrasts"]
        firstlevel_wf, connames = init_glm_wf(
            conditions,
            contrasts,
            repetition_time,
            metadata["UseMovPar"],
            name="glm_wf"
        )
        create_ds(wf, firstlevel_wf, connames, func_preproc_wf, temporalfilter_wf,
                  bold_file, output_dir, name="firstlevel")
        wfbywf["firstlevel_wf"] = firstlevel_wf
        outnamesbywf["firstlevel_wf"] = connames
    if "ConnectivitySeeds" in metadata:
        firstlevel_wf, seednames = init_seedconnectivity_wf(
            metadata["ConnectivitySeeds"],
            metadata["UseMovPar"],
            name="seedconnectivity_wf"
        )
        create_ds(wf, firstlevel_wf, seednames, func_preproc_wf, temporalfilter_wf,
                  bold_file, output_dir, name="seedconnectivity")
        wfbywf["seedconnectivity_wf"] = firstlevel_wf
        outnamesbywf["seedconnectivity_wf"] = seednames
    if "ICAMaps" in metadata:
        firstlevel_wf, componentnames = init_dualregression_wf(
            metadata["ICAMaps"],
            metadata["UseMovPar"],
            name="dualregression_wf"
        )
        create_ds(wf, firstlevel_wf, componentnames, func_preproc_wf, temporalfilter_wf,
                  bold_file, output_dir, name="dualregression")
        wfbywf["dualregression_wf"] = firstlevel_wf
        outnamesbywf["dualregression_wf"] = componentnames

    # ReHo
    if True:
        firstlevel_wf = init_reho_wf(
            name="reho_wf"
        )
        create_ds(wf, firstlevel_wf, ["reho"], func_preproc_wf, temporalfilter_wf,
                  bold_file, output_dir, name="reho")
        wfbywf["reho_wf"] = firstlevel_wf
        outnamesbywf["reho_wf"] = ["reho"]

    # ALFF
    if True:
        firstlevel_wf = create_alff(
            name="alff_wf"
        )
        create_ds(wf, firstlevel_wf, ["alff"], func_preproc_wf, temporalfilter_wf,
                  bold_file, output_dir, name="alff")
        wfbywf["alff_wf"] = firstlevel_wf
        outnamesbywf["alff_wf"] = ["alff"]

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=flatten([[["%s_cope" % w,
                              "%s_varcope" % w, "%s_mask_file" % w, "%s_dof_file" % w] for w in v] for v in
                            outnamesbywf.values()])
        ),
        name="outputnode")

    for k, v in outnamesbywf.items():
        for w in v:
            wf.connect(wfbywf[k], "outputnode.%s_cope" % w, outputnode, "%s_cope" % w)
            wf.connect(wfbywf[k], "outputnode.%s_varcope" % w, outputnode, "%s_varcope" % w)
            wf.connect(func_preproc_wf, "outputnode.bold_mask_mni", outputnode, "%s_mask_file" % w)
            wf.connect(wfbywf[k], "outputnode.dof_file", outputnode, "%s_dof_file" % w)

    outnames = sum(outnamesbywf.values(), [])
    return outnames
