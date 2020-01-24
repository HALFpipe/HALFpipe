# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import io as nio
from nipype.interfaces import fsl

from fmriprep.workflows.anatomical import init_anat_preproc_wf
from fmriprep.workflows.bold import init_func_preproc_wf
from fmriprep.interfaces.bids import DerivativesDataSink

from ..fmriprepsettings import (
    anatSettings,
    funcSettings
)

from .temporalfilter import init_temporalfilter_wf
from .tsnr import init_tsnr_wf

from .rest import init_rest_wf
from .task import init_glm_wf

from .derivatives import make_firstlevel_datasink

from .patch import patch_wf
from .fake import FakeBIDSLayout

from ..utils import lookup
from .utils import (
    make_varname,
    make_outputnode
)

from ..interface import (
    # ApplyXfmSegmentation,
    MotionCutoff,
    LogicalAnd,
    QualityCheck
)

_func_inputnode_fields = [
    "t1_preproc", "t1_brain", "t1_mask", "t1_seg",
    "t1_tpms", "t1_aseg", "t1_aparc",
    "t1_2_mni_forward_transform", "t1_2_mni_reverse_transform",
    "subjects_dir", "subject_id",
    "t1_2_fsnative_forward_transform", "t1_2_fsnative_reverse_transform"
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
        name="T1w",
        reportlets_dir=fmriprep_reportlets_dir,
        output_dir=fmriprep_output_dir,
        num_t1w=1,
        **anatSettings
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
        bold_file=bold_file,
        layout=layout,
        reportlets_dir=fmriprep_reportlets_dir,
        output_dir=fmriprep_output_dir,
        **funcSettings)

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

    ds_preproc = pe.Node(
        interface=nio.DataSink(
            base_directory=output_dir,
            source_file=bold_file,
            suffix="preproc"
        ),
        name="ds_preproc", run_without_submitting=True
    )

    ds_mask = pe.Node(
        interface=DerivativesDataSink(
            base_directory=output_dir,
            source_file=bold_file,
            suffix="mask"
        ),
        name="ds_mask", run_without_submitting=True
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
            ("outputnode.nonaggr_denoised_file", "inputnode.bold_file")
        ]),
        (temporalfilter_wf, maskpreproc, [
            ("outputnode.filtered_file", "in_file")
        ]),
        (func_preproc_wf, maskpreproc, [
            ("outputnode.bold_mask_mni", "mask_file")
        ]),
        (func_preproc_wf, ds_mask, [
            ("outputnode.bold_mask_mni", "in_file")
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
                ("outputnode.bold_mask_mni", "inputnode.mask_file"),
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
                    ("outputnode.bold_mask_mni", varname)
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
