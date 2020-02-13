# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import io as nio
from nipype.interfaces import fsl

from smriprep.workflows.anatomical import init_anat_preproc_wf

import fmriprep.workflows.bold
from fmriprep.workflows.bold import init_func_preproc_wf
from fmriprep.interfaces import DerivativesDataSink

from niworkflows.interfaces.utility import KeySelect

from ..fmriprepsettings import settings as fmriprepsettings

from .confounds import init_confounds_wf
from .temporalfilter import init_temporalfilter_wf
from .tsnr import init_tsnr_wf

from .rest import init_rest_wf
from .task import init_glm_wf

from .derivatives import (
    get_container_path,
    make_firstlevel_datasink
)

from .patch import patch_wf
from .fake import FakeBIDSLayout
from .memory import MemoryCalculator

from ..utils import (
    lookup
)
from .utils import (
    make_varname,
    make_outputnode,
    dataSinkRegexpSubstitutions
)

from ..interface import (
    # ApplyXfmSegmentation,
    MotionCutoff,
    LogicalAnd,
    QualityCheck
)

_anat2func_fields = [
    "t1w_preproc", "t1w_brain", "t1w_mask", "t1w_dseg",
    "t1w_aseg", "t1w_aparc", "t1w_tpms",
    "template",
    "anat2std_xfm", "std2anat_xfm",
    "joint_template", "joint_anat2std_xfm", "joint_std2anat_xfm",
    "subjects_dir", "subject_id",
    "fsnative2t1w_xfm"
]


def _get_wf_name(bold_fname):
    return "fmriprep"


fmriprep.workflows.bold._get_wf_name = _get_wf_name


def init_subject_wf(item, workdir, images, data):
    """
    initialize workflow for all scans of a single subject
    :param item: input item (key/value tuple) from dictionary
    :param workdir: the working directory
    :param images: the images data structure from pipeline.json
    :param data: the entire pipeline.json
    """

    fmriprep_output_dir = op.join(workdir, "fmriprep_output")
    fmriprep_reportlets_dir = op.join(workdir, "qualitycheck")
    output_dir = op.join(workdir, "intermediates")

    metadata = data["metadata"]
    subject, subjectdata = item

    subject_wf = pe.Workflow(name="sub_" + subject)

    # assert structural data
    if "T1w" not in subjectdata:
        return subject_wf

    anat_preproc_wf = init_anat_preproc_wf(
        fmriprepsettings.bids_dir,
        fmriprepsettings.freesurfer,
        fmriprepsettings.hires,
        fmriprepsettings.longitudinal,
        fmriprepsettings.omp_nthreads,
        fmriprep_output_dir,
        fmriprepsettings.output_spaces,
        1,  # num_t1w
        fmriprep_reportlets_dir,
        fmriprepsettings.skull_strip_template,
        debug=fmriprepsettings.debug,
        name="smriprep"
    )
    anat_preproc_wf.get_node("inputnode").inputs.t1w = subjectdata["T1w"]

    anat_outputnode = anat_preproc_wf.get_node("outputnode")
    anat_helper = pe.Node(
        interface=niu.IdentityInterface(
            fields=[
                "std_tpms"
            ],
        ),
        name="anat_helper"
    )
    subject_wf.connect([
        (anat_preproc_wf, anat_helper, [
            ("anat_norm_wf.outputnode.std_tpms", "std_tpms")
        ])
    ])

    outfieldsByOutnameByScan = {}

    for i, (scanname, scandata) in enumerate(subjectdata.items()):
        # skip anatomical
        if scanname == "T1w":
            continue

        scan_wf = pe.Workflow(name="scan_" + scanname)

        scanmetadata = metadata[scanname]
        try:
            scanmetadata["RepetitionTime"] = \
                scanmetadata["RepetitionTime"][subject]
        except TypeError:
            pass
        keys = ["SmoothingFWHM", "TemporalFilter", "MotionCutoff"]
        for k in keys:
            if k in metadata:
                scanmetadata[k] = metadata[k]

        if isinstance(scandata, dict):  # multiple runs
            for runname, bold_file in scandata.items():
                run_wf = pe.Workflow(name="run_" + runname)

                _ = init_func_wf(
                    run_wf,
                    anat_outputnode, anat_helper,
                    scandata, scanmetadata,
                    workdir,
                    fmriprep_reportlets_dir,
                    fmriprep_output_dir,
                    output_dir,
                    subject=subject, scan=scanname, run=runname
                )
        else:  # one run
            outfieldsByOutnameByScan[scanname] = init_func_wf(
                scan_wf,
                anat_outputnode, anat_helper,
                scandata, scanmetadata,
                workdir,
                fmriprep_reportlets_dir,
                fmriprep_output_dir,
                output_dir,
                subject=subject, scan=scanname
            )

    subject_wf = patch_wf(subject_wf,
                          images, output_dir,
                          fmriprep_reportlets_dir, fmriprep_output_dir)

    return subject, subject_wf, outfieldsByOutnameByScan


def init_func_wf(wf,
                 anat_outputnode, anat_helper,
                 bold_file, metadata,
                 workdir,
                 fmriprep_reportlets_dir,
                 fmriprep_output_dir,
                 output_dir,
                 subject, scan=None, run=None):
    """Initialize workflow for single functional image

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
        fmriprepsettings.aroma_melodic_dim,
        fmriprepsettings.bold2t1w_dof,
        bold_file,
        fmriprepsettings.cifti_output,
        fmriprepsettings.debug,
        None,  # dummy_scans
        fmriprepsettings.err_on_aroma_warn,
        fmriprepsettings.fmap_bspline,
        fmriprepsettings.fmap_demean,
        fmriprepsettings.force_syn,
        fmriprepsettings.freesurfer,
        fmriprepsettings.ignore,
        fmriprepsettings.low_mem,
        fmriprepsettings.medial_surface_nan,
        fmriprepsettings.omp_nthreads,
        fmriprep_output_dir,
        fmriprepsettings.output_spaces,
        fmriprepsettings.regressors_all_comps,
        fmriprepsettings.regressors_dvars_th,
        fmriprepsettings.regressors_fd_th,
        fmriprep_reportlets_dir,
        fmriprepsettings.t2s_coreg,
        fmriprepsettings.use_aroma,
        fmriprepsettings.use_bbr,
        fmriprepsettings.use_syn,
        layout=layout, num_bold=1)

    # adjust smoothing
    for node in func_preproc_wf._get_all_nodes():
        if type(node._interface) is fsl.SUSAN:
            node._interface.inputs.fwhm = float(metadata["SmoothingFWHM"])

    # connect fmriprep inputs
    wf.connect([
        (anat_outputnode, func_preproc_wf, [
            (f, "inputnode.%s" % f)
            for f in _anat2func_fields
        ]),
    ])

    memcalc = MemoryCalculator(bold_file)
    repetition_time = metadata["RepetitionTime"]

    # select standard space
    select_std = pe.Node(
        interface=KeySelect(
            fields=["bold_file", "mask_file", "tpms"]),
        name="select_std"
    )
    select_std.inputs.key = "MNI152NLin6Asym"
    wf.connect([
        (func_preproc_wf, select_std, [
            ("outputnode.nonaggr_denoised_file", "bold_file"),
            ("outputnode.bold_mask_std",  "mask_file"),
            ("bold_std_trans_wf.outputnode.templates", "keys")
        ]),
        (anat_helper, select_std, [
            ("std_tpms", "tpms")
        ])
    ])

    # mask bold file
    maskpreproc = pe.Node(
        interface=fsl.ApplyMask(),
        name="mask_preproc",
        mem_gb=memcalc.series_std_gb
    )
    wf.connect([
        (select_std, maskpreproc, [
            ("bold_file", "in_file"),
            ("mask_file", "mask_file")
        ])
    ])

    # shortcut
    helper = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file", "mask_file",
                    "tpms", "movpar_file", "skip_vols"]),
        name="helper",
        run_without_submitting=True,
        mem_gb=memcalc.min_gb
    )
    wf.connect([
        (maskpreproc, helper, [
            ("out_file", "bold_file")
        ]),
        (select_std, helper, [
            ("mask_file", "mask_file"),
            ("tpms", "tpms")
        ]),
        (func_preproc_wf, helper, [
            ("bold_hmc_wf.outputnode.movpar_file", "movpar_file"),
            ("bold_reference_wf.outputnode.skip_vols", "skip_vols")
        ])
    ])

    # recalculate confounds
    confounds_wf = init_confounds_wf(
        metadata,
        memcalc=memcalc
    )
    wf.connect([
        (helper, confounds_wf, [
            ("bold_file", "inputnode.bold_file"),
            ("mask_file", "inputnode.mask_file"),
            ("skip_vols", "inputnode.skip_vols"),
            ("movpar_file", "inputnode.movpar_file"),
            ("tpms", "inputnode.tpms"),
        ])
    ])

    # copy preproc and mask
    ds_scan = pe.Node(
        interface=nio.DataSink(
            infields=["preproc", "mask"],
            regexp_substitutions=dataSinkRegexpSubstitutions,
            base_directory=output_dir,
            container=get_container_path(subject, scan, run),
            suffix="preproc",
            parameterization=False,
            force_run=True
        ),
        name="ds_scan", run_without_submitting=True,
        mem_gb=memcalc.min_gb
    )
    wf.connect([
        (helper, ds_scan, [
            ("bold_file", "preproc"),
            ("mask_file", "mask")
        ])
    ])

    # high pass filter
    temporalfilter_wf = init_temporalfilter_wf(
        metadata["TemporalFilter"],
        repetition_time,
        memcalc=memcalc
    )
    wf.connect([
        (helper, temporalfilter_wf, [
            ("bold_file", "inputnode.bold_file")
        ])
    ])

    # calculate tsnr image
    tsnr_wf = init_tsnr_wf()
    ds_tsnr = pe.Node(
        interface=DerivativesDataSink(
            base_directory=fmriprep_reportlets_dir,
            source_file=bold_file,
            suffix="tsnr"
        ),
        name="ds_tsnr", run_without_submitting=True,
        mem_gb=memcalc.min_gb
    )
    wf.connect([
        (temporalfilter_wf, tsnr_wf, [
            ("outputnode.filtered_file", "inputnode.bold_file")
        ]),
        (tsnr_wf, ds_tsnr, [
            ("outputnode.report_file", "in_file")
        ])
    ])

    outByWorkflowName = {}

    def aggregate(out):
        firstlevel_wf, outnames, outfields = out

        if len(outnames) == 0:
            return

        outByWorkflowName[firstlevel_wf.name] = out

        make_firstlevel_datasink(
            wf,
            firstlevel_wf, outnames, outfields,
            output_dir, subject, scan, run
        )

    # first level stats workflows
    if "Conditions" in metadata:
        conditions = lookup(metadata["Conditions"],
                            subject_id=subject, run_id=run)
        aggregate(init_glm_wf(
            metadata, conditions
        ))
    aggregate(init_rest_wf(
        metadata
    ))

    # connect inputs
    for workflowName, (firstlevel_wf, outnames, outfields) \
            in outByWorkflowName.items():
        wf.connect([
            (helper, firstlevel_wf, [
                ("bold_file", "inputnode.bold_file"),
                ("mask_file", "inputnode.mask_file")
            ]),
            (confounds_wf, firstlevel_wf, [
                ("outputnode.confounds", "inputnode.confounds"),
            ])
        ])

    outputnode, outfieldsByOutname = \
        make_outputnode(wf, outByWorkflowName,
                        ["mask_file"], ["keep"])

    # add mask file
    for workflowName, (firstlevel_wf, outnames, outfields) \
            in outByWorkflowName.items():
        for outname in outnames:
            varname = make_varname(outname, "mask_file")
            wf.connect([
                (helper, outputnode, [
                    ("mask_file", varname)
                ])
            ])

    qualitycheck = pe.Node(
        name="qualitycheck",
        interface=QualityCheck()
    )
    qualitycheck.inputs.base_directory = workdir
    qualitycheck.inputs.subject = subject
    qualitycheck.inputs.scan = scan
    if run is not None:
        qualitycheck.inputs.run = run

    if "MotionCutoff" in metadata:
        # checks for motion above the cutoffs
        motioncutoff = pe.Node(
            interface=MotionCutoff(),
            name="motioncutoff",
            run_without_submitting=True,
            mem_gb=memcalc.min_gb
        )
        motioncutoff.inputs.mean_fd_cutoff = \
            metadata["MotionCutoff"]["MeanFDCutoff"]
        motioncutoff.inputs.fd_greater_0_5_cutoff = \
            metadata["MotionCutoff"]["ProportionFDGt0_5Cutoff"]

        logicaland = pe.Node(
            interface=LogicalAnd(numinputs=2),
            name="logicaland",
            run_without_submitting=True,
            mem_gb=memcalc.min_gb
        )

        wf.connect([
            (func_preproc_wf, motioncutoff, [
                ("outputnode.confounds", "confounds"),
            ]),
            (motioncutoff, logicaland, [
                ("keep", "in1")
            ]),
            (qualitycheck, logicaland, [
                ("keep", "in2")
            ]),
            (logicaland, outputnode, [
                ("out", "keep")
            ])
        ])
    else:
        wf.connect([
            (qualitycheck, outputnode, [
                ("keep", "keep")
            ]),
        ])

    return outfieldsByOutname
