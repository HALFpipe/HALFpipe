# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
from nipype.interfaces import afni

from niworkflows.interfaces.utility import KeySelect

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
    def __init__(self, attrs, keyAttr=None, keyVal=None, keySelectAttrs=None):
        self._attrs = attrs
        self._keyAttr = keyAttr
        self._keyVal = keyVal
        self._keySelectAttrs = keySelectAttrs

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
                        for attr in self._attrs
                    ],
                )
            ]
        )
        if self._keyAttr is not None:
            assert self._keyVal is not None
            assert self._keySelectAttrs is not None and len(self._keySelectAttrs) > 0

            selectnodename = f"keyselect_from_{out_wf.name}_to_{in_wf.name}"
            select = parentworkflow.get_node(selectnodename)
            if select is None:
                select = pe.Node(
                    interface=KeySelect(fields=self._keySelectAttrs, key=self._keyVal),
                    name=selectnodename,
                    run_without_submitting=True,
                )
                parentworkflow.connect(out_wf, self._keyAttr, select, "keys")
                parentworkflow.connect(
                    [
                        (
                            out_wf,
                            select,
                            [(f"{out_nodename}{attr}", attr) for attr in self._keySelectAttrs],
                        ),
                    ]
                )
            parentworkflow.connect(
                [
                    (
                        select,
                        in_wf,
                        [(attr, f"{in_nodename}{attr}") for attr in self._keySelectAttrs],
                    ),
                ]
            )
