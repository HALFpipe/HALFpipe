# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
from nipype.pipeline import engine as pe


def init_bypass_wf(attrs=[], unconnected_attrs=[], name=None, suffix=None):
    """
    This function initializes an instance of the Nipype Workflow class
    that bypasses its input to the output. This allows you to skip a step in preprocessing
    (i.e. a node in the workflow) without having to disconnect all of its inputs and outputs.

    Parameters
    ----------
    attrs : list of str
        List of attribute names to be passed through the workflow.
    unconnected_attrs : list of str
        List of unconnected attribute names to be included in the output node.
    name : str, optional
        Name of the workflow. If not provided, a generic name will be used.
    suffix : str, optional
        Suffix to append to the workflow name for better identification.

    Returns
    -------
    workflow : nipype.pipeline.engine.workflows.Workflow
        The initialized Nipype workflow with input and output nodes connected.
    """

    if suffix is not None:
        name = f"{name}_{suffix}"

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=niu.IdentityInterface(fields=[*attrs]),
        name="inputnode",
    )
    outputnode = pe.Node(
        interface=niu.IdentityInterface(fields=[*attrs, *unconnected_attrs]),
        name="outputnode",
    )

    for attr in attrs:
        workflow.connect(inputnode, attr, outputnode, attr)

    return workflow
