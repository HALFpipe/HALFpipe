# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
from nipype.pipeline import engine as pe


def init_bypass_wf(attrs: list | None = None, unconnected_attrs: list | None = None, name=None, suffix=None):
    """
    This function initializes a Nipype Workflow that can be used as a drop-in
    replacement for another workflow, but that doesn't do any processing.
    All the inputs defined by attrs will be passed directly to the outputnode.

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
        The initialized Nipype workflow with inputnode and outputnode connected.
    """
    attrs = [] if attrs is None else attrs
    unconnected_attrs = [] if unconnected_attrs is None else unconnected_attrs

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
