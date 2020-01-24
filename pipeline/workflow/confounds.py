# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from ..interface import SelectColumnsTSV


def make_confounds_selectcolumns(metadata):
    # create design matrix
    selectcolumns = pe.Node(
        interface=SelectColumnsTSV(),
        name="selectcolumns",
        run_without_submitting=True
    )

    column_names = []
    if metadata["UseMovPar"]:
        column_names.extend(["X", "Y", "Z", "RotX", "RotY", "RotZ"])
    if metadata["CSF"]:
        column_names.append("CSF")
    if metadata["Whitematter"]:
        column_names.append("WhiteMatter")
    if metadata["GlobalSignal"]:
        column_names.append("GlobalSignal")

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
            ("confounds", "design_file"),
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
