# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
from nipype.pipeline import engine as pe


def init_bypass_wf(attrs=[], unconnected_attrs=[], name=None, suffix=None):
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
