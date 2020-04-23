# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re

import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu

from niworkflows.interfaces.utility import KeySelect

from ..interface import ResultdictDatasink, MakeResultdicts, ReportResultdictDatasink
from ..utils import hexdigest, first

reportlets_datasink_match = re.compile(r"ds_?(.*?)_?report_?(.*?)").fullmatch


def make_resultdict_datasink(workflow, base_directory, endpoint, name="resultdictdatasink"):
    resultdictdatasink = pe.Node(
        interface=ResultdictDatasink(base_directory=str(base_directory)), name=name
    )
    workflow.connect(*endpoint, resultdictdatasink, "indicts")


def make_reportnode_datasink(workflow, workdir):
    reportdatasink = pe.Node(
        interface=ReportResultdictDatasink(base_directory=str(workdir)), name="reportdatasink",
    )
    reportnode = workflow.get_node("reportnode")
    workflow.connect(reportnode, "resultdicts", reportdatasink, "indicts")


def make_reportnode(workflow, spaces=False):
    nodepaths = []
    for nodepath in workflow.list_node_names():
        hierarchy = nodepath.split(".")
        nodename = hierarchy[-1]
        if reportlets_datasink_match(nodename) is not None:
            nodepaths.append(nodepath)

    connecttupls = []
    for nodepath in nodepaths:
        hierarchy = nodepath.split(".")
        parentpath = ".".join(hierarchy[:-1])
        parent = workflow.get_node(parentpath)
        node = workflow.get_node(nodepath)
        ancestorname = hierarchy[0]
        ancestor = workflow.get_node(ancestorname)
        path_from_ancestor = ".".join(hierarchy[1:-1])
        connecttupls.append((node, parent, ancestor, path_from_ancestor))

    mergedesc = pe.Node(
        interface=niu.Merge(len(connecttupls)), name="mergedesc", run_without_submitting=True,
    )
    mergereport = pe.Node(
        interface=niu.Merge(len(connecttupls)),
        name="mergereport",
        run_without_submitting=True,
    )

    spacendpoint = None

    for i, (node, parent, ancestor, path_from_ancestor) in enumerate(connecttupls):
        for (u, v, c) in parent._graph.in_edges([node], data=True):
            for outattrname, inattrname in c["connect"]:
                funcplusargs = None
                if isinstance(outattrname, (tuple, list)):
                    funcplusargs = outattrname[1:]
                    outattrname = first(outattrname)
                outpath = f"{u.name}.{outattrname}"
                if len(path_from_ancestor) > 0:
                    outpath = f"{path_from_ancestor}.{outpath}"
                if funcplusargs is not None:
                    outpath = (outpath, *funcplusargs)
                if inattrname == "in_file":
                    workflow.connect([(ancestor, mergereport, [(outpath, f"in{i+1}")])])
                elif inattrname == "space":
                    spacendpoint = (ancestor, outpath)
        if isinstance(node.inputs.desc, str) and len(node.inputs.desc) > 0:
            desc = node.inputs.desc
        else:
            desc = "".join(reportlets_datasink_match(node.name).groups())
        assert isinstance(desc, str) and len(desc) > 0
        setattr(mergedesc.inputs, f"in{i+1}", desc)
        parent.remove_nodes([node])

    reportnode = pe.Node(
        interface=MakeResultdicts(keys=["desc", "report", "space"]), name="reportnode"
    )
    workflow.connect(workflow.get_node("inputnode"), "metadata", reportnode, "basedict")
    workflow.connect(mergedesc, "out", reportnode, "desc")
    workflow.connect(mergereport, "out", reportnode, "report")
    if spaces:
        workflow.connect([(spacendpoint[0], reportnode, [(spacendpoint[1], "space")])])


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

            hexval = hexdigest((self._keyAttr, self._keyVal, self._keySelectAttrs))
            selectnodename = f"keyselect_from_{out_wf.name}_{hexval}"
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
