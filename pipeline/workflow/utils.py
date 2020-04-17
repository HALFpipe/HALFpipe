# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
from nipype.interfaces import afni

from ..interface import ResultdictDatasink


def convert_afni_endpoint(workflow, endpoint):
    node, attr = endpoint
    name = node.name

    afnitonifti = pe.Node(afni.AFNItoNIFTI(), name=f"{name}_{attr}_afnitonifti")

    workflow.connect(*endpoint, afnitonifti, "in_file")
    return (afnitonifti, "out_file")


def make_resultdict_datasink(workflow, base_directory, endpoint, name="resultdictdatasink"):
    resultdictdatasink = pe.Node(
        interface=ResultdictDatasink(base_directory=str(base_directory)), name=name
    )
    workflow.connect(*endpoint, resultdictdatasink, "indicts")


class ConnectAttrlistHelper:
    def __init__(self, attrlist):
        self._attrlist = attrlist

    def __call__(
        self, parentworkflow, out_wf, in_wf, out_nodename="outputnode", in_nodename="inputnode"
    ):
        if out_nodename is None:
            out_nodename = ""
        else:
            out_nodename = f"{out_nodename}."
        if in_nodename is None:
            in_nodename = ""
        else:
            in_nodename = f"{in_nodename}."
        parentworkflow.connect(
            [
                (
                    out_wf,
                    in_wf,
                    [
                        (f"{out_nodename}{attr}", f"{in_nodename}{attr}")
                        for attr in self._attrlist
                    ],
                )
            ]
        )
