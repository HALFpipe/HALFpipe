# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import io as nio
from nipype.interfaces import fsl

from smriprep.workflows.anatomical import init_anat_preproc_wf

from fmriprep.workflows.bold import init_func_preproc_wf
from fmriprep.interfaces import DerivativesDataSink

from ..fmriprepsettings import settings as fmriprepsettings

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

from ..utils import (
    lookup,
    _get_first
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

_func_inputnode_fields = [
    "t1w_preproc", "t1w_brain", "t1w_mask", "t1w_dseg",
    "t1w_aseg", "t1w_aparc", "t1w_tpms",
    "template",
    "anat2std_xfm", "std2anat_xfm",
    "joint_template", "joint_anat2std_xfm", "joint_std2anat_xfm",
    "subjects_dir", "subject_id",
    "fsnative2t1w_xfm"
]


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
        name="T1w"
    )
    anat_inputnode = anat_preproc_wf.get_node("inputnode")
    anat_inputnode.inputs.t1w = subjectdata["T1w"]

    outfieldsByOutnameByScan = {}

    for i, (scanname, scandata) in enumerate(subjectdata.items()):
        # skip anatomical
        if scanname == "T1w":
            continue

        scan_wf = pe.Workflow(name="scan_" + scanname)

        inputnode = pe.Node(
            interface=niu.IdentityInterface(
                fields=_func_inputnode_fields,
            ),
            name="inputnode"
        )
        scan_wf.add_nodes((inputnode,))

        subject_wf.connect([
            (anat_preproc_wf, scan_wf, [
                ("outputnode.%s" % f, "inputnode.%s" % f)
                for f in _func_inputnode_fields
            ])
        ])

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
            raise NotImplementedError("To be implemented")
        else:  # one run
            outfieldsByOutnameByScan[scanname] = init_func_wf(
                scan_wf, inputnode, scandata, scanmetadata,
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


def init_func_wf(wf, inputnode, bold_file, metadata,
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

    # apply_xfm = pe.Node(
    #     interface=ApplyXfmSegmentation(),
    #     name="apply_xfm"
    # )

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
        name="ds_scan", run_without_submitting=True
    )

    tsnr_wf = init_tsnr_wf()
    ds_tsnr = pe.Node(
        interface=DerivativesDataSink(
            base_directory=fmriprep_reportlets_dir,
            source_file=bold_file,
            suffix="tsnr"
        ),
        name="ds_tsnr", run_without_submitting=True
    )

    wf.connect([
        (inputnode, func_preproc_wf, [
            (f, "inputnode.%s" % f)
            for f in _func_inputnode_fields
        ]),
        (func_preproc_wf, temporalfilter_wf, [
            (("outputnode.bold_std", _get_first), "inputnode.bold_file")
        ]),
        (temporalfilter_wf, maskpreproc, [
            ("outputnode.filtered_file", "in_file")
        ]),
        (func_preproc_wf, maskpreproc, [
            (("outputnode.bold_mask_std", _get_first), "mask_file")
        ]),
        (func_preproc_wf, ds_scan, [
            (("outputnode.bold_mask_std", _get_first), "preproc")
        ]),
        (maskpreproc, ds_scan, [
            ("out_file", "mask")
        ]),

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
            (func_preproc_wf, firstlevel_wf, [
                (("outputnode.bold_mask_std", _get_first),
                    "inputnode.mask_file"),
                ("outputnode.confounds", "inputnode.confounds"),
            ]),
            (maskpreproc, firstlevel_wf, [
                ("out_file", "inputnode.bold_file"),
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
                (func_preproc_wf, outputnode, [
                    (("outputnode.bold_mask_std", _get_first), varname)
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
            name="motioncutoff"
        )
        motioncutoff.inputs.mean_fd_cutoff = \
            metadata["MotionCutoff"]["MeanFDCutoff"]
        motioncutoff.inputs.fd_greater_0_5_cutoff = \
            metadata["MotionCutoff"]["ProportionFDGt0_5Cutoff"]

        logicaland = pe.Node(
            interface=LogicalAnd(numinputs=2),
            name="logicaland"
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
