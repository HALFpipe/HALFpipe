# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import afni
from nipype.interfaces import fsl

from fmriprep.workflows.bold import init_bold_confs_wf

from .smooth import init_smooth_wf
from ..interface import SelectColumnsTSV

from .memory import MemoryCalculator
from ..utils import first, hexdigest
from ..ui.utils import forbidden_chars
from .utils import convert_afni_endpoint, ConnectAttrlistHelper
from ..fmriprepconfig import config as fmriprepconfig


in_attrs_from_anat_preproc_wf = [
    "t1w_tpms",
    "t1w_mask",
    "anat2std_xfm",
]

in_attrs_from_func_preproc_wf = [
    "bold_std",
    "nonaggr_denoised_file",
    "bold_mask_std",
    "movpar_file",
    "skip_vols",
    "aroma_confounds",
]


def get_repetition_time(dic):
    return dic.get("RepetitionTime")


def make_confoundsendpoint(prefix, workflow, boldfileendpoint, confoundnames, memcalc):
    inputnode = workflow.get_node("inputnode")

    bold_confounds_wf = init_bold_confs_wf(
        mem_gb=memcalc.series_std_gb,
        metadata={},
        regressors_all_comps=fmriprepconfig.regressors_all_comps,
        regressors_fd_th=fmriprepconfig.regressors_fd_th,
        regressors_dvars_th=fmriprepconfig.regressors_dvars_th,
        name=f"{prefix}_bold_confounds_wf",
    )

    bold_confounds_wf.get_node("inputnode").inputs.t1_transform_flags = [False]
    workflow.connect(*boldfileendpoint, bold_confounds_wf, "inputnode.bold")
    workflow.connect(
        [
            (
                inputnode,
                bold_confounds_wf,
                [
                    ("bold_mask_std", "inputnode.bold_mask"),
                    ("skip_vols", "inputnode.skip_vols"),
                    ("t1w_tpms", "inputnode.t1w_tpms"),
                    ("t1w_mask", "inputnode.t1w_mask"),
                    ("movpar_file", "inputnode.movpar_file"),
                    ("anat2std_xfm", "inputnode.t1_bold_xform"),
                ],
            ),
            (
                inputnode,
                bold_confounds_wf,
                [
                    (("metadata", get_repetition_time), "acompcor.repetition_time"),
                    (("metadata", get_repetition_time), "tcompcor.repetition_time"),
                ],
            ),
        ]
    )

    selectcolumns = pe.Node(
        SelectColumnsTSV(column_names=list(confoundnames), output_with_header=False),
        run_without_submitting=True,
        mem_gb=memcalc.min_gb,
        name=f"{prefix}_selectcolumns",
    )
    workflow.connect(bold_confounds_wf, "outputnode.confounds_file", selectcolumns, "in_file")

    return (selectcolumns, "out_file")


def init_bold_filt_wf(variant=None, memcalc=MemoryCalculator()):
    assert variant is not None

    tagdict = dict(variant)

    name = "filt"
    for key, value in tagdict.items():
        if not isinstance(value, str) or forbidden_chars.search(value) is not None:
            value = hexdigest(value)
        name += f"_{key}_{value}"

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[*in_attrs_from_func_preproc_wf, *in_attrs_from_anat_preproc_wf, "metadata"]
        ),
        name="inputnode",
    )
    workflow.add_nodes([inputnode])

    bandpass = None

    ortendpoint = None

    boldfileendpoint = (inputnode, "bold_std")

    if "smoothed" in tagdict:
        fwhm = tagdict["smoothed"]
        assert isinstance(fwhm, float)
        if np.isclose(fwhm, 6.0):
            if "confounds_removed" in tagdict:
                if "aroma_motion_[0-9]+" in tagdict["confounds_removed"]:
                    del tagdict["smoothed"]
                    newconfoundsremoved = [
                        name
                        for name in tagdict["confounds_removed"]
                        if name != "aroma_motion_[0-9]+"
                    ]
                    if len(newconfoundsremoved) == 0:
                        del tagdict["confounds_removed"]
                    else:
                        tagdict["confounds_removed"] = newconfoundsremoved
                    boldfileendpoint = (inputnode, "nonaggr_denoised_file")
        else:
            smooth_workflow = init_smooth_wf(fwhm=fwhm)
            workflow.connect(
                inputnode, "bold_mask_std", smooth_workflow, "inputnode.mask_file"
            )
            workflow.connect(*boldfileendpoint, smooth_workflow, "inputnode.in_file")
            boldfileendpoint = (smooth_workflow, "outputnode.out_file")

    if "band_pass_filtered" in tagdict:
        type, args = tagdict["band_pass_filtered"]
        if type == "frequency_based":
            bandpass = args
        elif type == "gaussian":
            gaussianfilter = pe.Node(
                fsl.TemporalFilter(highpass_sigma=first(args)), name="gaussianfilter"
            )
            workflow.connect(*boldfileendpoint, gaussianfilter, "in_file")
            boldfileendpoint = (gaussianfilter, "out_file")

    if "confounds_removed" in tagdict:
        confoundnames = tagdict["confounds_removed"]
        ortendpoint = make_confoundsendpoint(
            "remove", workflow, boldfileendpoint, confoundnames, memcalc
        )

    if bandpass is not None or ortendpoint is not None:
        tproject = pe.Node(afni.TProject(polort=1), name="tproject")
        workflow.connect([(inputnode, tproject, [(("metadata", get_repetition_time), "TR")])])
        if bandpass is not None:
            tproject.inputs.bandpass = bandpass
        if ortendpoint is not None:
            workflow.connect(*ortendpoint, tproject, "ort")
        boldfileendpoint = convert_afni_endpoint(workflow, (tproject, "out_file"))

    endpoints = [boldfileendpoint]  # boldfile is finished

    if "confounds_extract" in tagdict:  # last
        confoundnames = tagdict["confounds_extract"]
        confoundsextractendpoint = make_confoundsendpoint(
            "extract", workflow, boldfileendpoint, confoundnames, memcalc
        )
        endpoints.append(confoundsextractendpoint)

    outnames = [f"out{i+1}" for i in range(len(endpoints))]

    outputnode = pe.Node(niu.IdentityInterface(fields=outnames), name="outputnode",)

    for outname, endpoint in zip(outnames, endpoints):
        workflow.connect(*endpoint, outputnode, outname)

    return workflow


# Utility functions
connect_filt_wf_attrs_from_anat_preproc_wf = ConnectAttrlistHelper(
    in_attrs_from_anat_preproc_wf
)
connect_filt_wf_attrs_from_func_preproc_wf = ConnectAttrlistHelper(
    in_attrs_from_func_preproc_wf
)
