# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl
from nipype.interfaces.ants.resampling import ApplyTransforms

from fmriprep.workflows.bold import init_bold_confs_wf

from ..interface import (
    SelectColumnsTSV,
    DontApplyTransforms
)

from .memory import MemoryCalculator
from ..fmriprepsettings import settings as fmriprepsettings


def init_confounds_wf(metadata,
                      name="confounds",
                      memcalc=MemoryCalculator()):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file", "mask_file",
                    "tpms", "movpar_file", "skip_vols"]),
        name="inputnode"
    )

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["confounds"]),
        name="outputnode"
    )

    mem_gb = memcalc.series_std_gb
    bold_confounds_wf = init_bold_confs_wf(
        mem_gb,
        metadata,
        regressors_all_comps=fmriprepsettings.regressors_all_comps,
        regressors_dvars_th=fmriprepsettings.regressors_dvars_th,
        regressors_fd_th=fmriprepsettings.regressors_fd_th,
    )

    # we are passing everything in standard space
    for nodename in bold_confounds_wf.list_node_names():
        node = bold_confounds_wf.get_node(nodename)
        if isinstance(node.interface, ApplyTransforms):
            node._interface = DontApplyTransforms()
    bold_confounds_wf.get_node("inputnode").inputs.t1_bold_xform = "identity"

    workflow.connect([
        (inputnode, bold_confounds_wf, [
            ("bold_file", "inputnode.bold"),
            ("mask_file", "inputnode.bold_mask"),
            ("skip_vols", "inputnode.skip_vols"),
            ("tpms", "inputnode.t1w_tpms"),
            ("mask_file", "inputnode.t1w_mask"),
            ("movpar_file", "inputnode.movpar_file")
        ]),
        (bold_confounds_wf, outputnode, [
            ("outputnode.confounds_file", "confounds"),
        ])
    ])

    return workflow


def make_confounds_selectcolumns(metadata):
    # create design matrix
    selectcolumns = pe.Node(
        interface=SelectColumnsTSV(),
        name="selectcolumns",
        run_without_submitting=True
    )

    column_names = []
    if "UseMovPar" in metadata and metadata["UseMovPar"]:
        column_names.extend(
            ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]
        )
    if "CSF" in metadata and metadata["CSF"]:
        column_names.append("csf")
    if "Whitematter" in metadata and metadata["Whitematter"]:
        column_names.append("white_matter")
    if "GlobalSignal" in metadata and metadata["GlobalSignal"]:
        column_names.append("global_signal")

    selectcolumns.inputs.column_names = column_names

    return selectcolumns, column_names


def init_confoundsregression_wf(metadata,
                                name="confoundsregression"):
    """
    create workflow to ccorrect for
    for covariates in functional scans
    :param use_movpars: if true, regress out movement parameters when
        calculating the glm
    :param use_csf: if true, regress out csf parameters when
        calculating the glm
    :param use_wm: if true, regress out white matter parameters when
        calculating the glm
    :param use_globalsignal: if true, regress out global signal
        parameters when calculating the glm
    """

    workflow = pe.Workflow(name=name)

    # inputs are the bold file, the mask file and the regression files
    inputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["bold_file", "mask_file", "confounds"]),
        name="inputnode"
    )

    selectcolumns, column_names = make_confounds_selectcolumns(
        metadata
    )

    if len(column_names) == 0:
        return

    regfilt = pe.Node(
        interface=fsl.FilterRegressor(),
        name="regfilt",
    )
    regfilt.inputs.filter_all = True

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=["filtered_file"]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, selectcolumns, [
            ("confounds", "in_file"),
        ]),
        (selectcolumns, regfilt, [
            ("out_file", "design_file"),
        ]),
        (inputnode, regfilt, [
            ("bold_file", "in_file"),
            ("mask_file", "mask"),
        ]),
        (regfilt, outputnode, [
            ("out_file", "filtered_file"),
        ]),
    ])

    return workflow
