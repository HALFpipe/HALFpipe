# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

import pytest

import os
from pathlib import Path

from halfpipe.workflow.execgraph import DontRunRunner
from halfpipe.plugins.multiproc import MultiProcPlugin
from halfpipe.plugins.reftracer import PathReferenceTracer


def add(a, b):
    return a + b


@pytest.mark.timeout(60)
@pytest.mark.parametrize("node_order_str", ["mpp", "forward", "backward"])
def test_PathReferenceTracer(tmp_path, node_order_str):
    import nipype.interfaces.utility as niu
    import nipype.pipeline.engine as pe

    os.chdir(str(tmp_path))

    wf = pe.Workflow("w", base_dir=Path.cwd())

    def make_node(name):
        return pe.Node(
            interface=niu.Function(
                function=add,
                input_names=["a", "b"],
                output_names=["c"]
            ),
            name=name
        )

    x = make_node("x")
    x.inputs.a = 1
    x.inputs.b = 2

    y = make_node("y")
    y.inputs.a = 7
    wf.connect(x, "c", y, "b")

    z = make_node("z")
    wf.connect(y, "c", z, "a")
    z.inputs.b = 1

    execgraph = wf.run(plugin=DontRunRunner())

    def get_node(name):
        for node in execgraph.nodes():
            if node.name == name:
                return node

    x = get_node("x")
    y = get_node("y")
    z = get_node("z")

    if node_order_str == "mpp":
        mpp = MultiProcPlugin(plugin_args=dict(keep="none"))
        mpp._generate_dependency_list(execgraph)

        rt = mpp._rt
    else:
        from nipype.pipeline.engine.utils import topological_sort

        rt = PathReferenceTracer()

        nodes, _ = topological_sort(execgraph)

        if node_order_str == "forward":
            pass
        elif node_order_str == "backward":
            nodes = nodes[::-1]

        for node in nodes:
            rt.add_node(node)
        for node in nodes:
            rt.set_node_pending(node)

    xrf = rt.node_resultfile_path(x)
    yrf = rt.node_resultfile_path(y)
    zrf = rt.node_resultfile_path(z)

    assert xrf in rt.black and yrf in rt.black and zrf in rt.black

    assert rt.refs[xrf] == set([yrf])
    assert rt.refs[yrf] == set([zrf])
    assert rt.refs[zrf] == set()

    assert rt.deps[xrf] == set([xrf.parent])
    assert rt.deps[yrf] == set([yrf.parent, xrf])
    assert rt.deps[zrf] == set([zrf.parent, yrf])

    rt.set_node_complete(x, True)

    assert xrf in rt.grey and yrf in rt.black and zrf in rt.black

    assert rt.refs[xrf] == set([yrf])
    assert rt.refs[yrf] == set([zrf])
    assert rt.refs[zrf] == set([])

    assert rt.deps[xrf] == set([xrf.parent])
    assert rt.deps[yrf] == set([yrf.parent, xrf])
    assert rt.deps[zrf] == set([zrf.parent, yrf])

    rt.set_node_complete(y, True)

    assert xrf in rt.white and yrf in rt.grey and zrf in rt.black

    assert rt.refs[xrf] == set([])
    assert rt.refs[yrf] == set([zrf])
    assert rt.refs[zrf] == set([])

    assert rt.deps[xrf] == set([xrf.parent])
    assert rt.deps[yrf] == set([yrf.parent])
    assert rt.deps[zrf] == set([zrf.parent, yrf])

    rtc = set(rt.collect())
    assert rtc == set([xrf, xrf.parent])

    rt.set_node_complete(y, True)  # test double complete


def totxt(a, b):
    from pathlib import Path

    afname = Path.cwd() / "a.txt"
    with open(afname, "w") as fp:
        fp.write(f"{a}\n")

    bfname = Path.cwd() / "b.txt"
    with open(bfname, "w") as fp:
        fp.write(f"{b}\n")

    return afname, bfname


def select(a, b):
    return b


@pytest.mark.timeout(60)
def test_PathReferenceTracer_indirect_refs(tmp_path):
    from nipype import config
    import nipype.interfaces.utility as niu
    import nipype.pipeline.engine as pe

    os.chdir(str(tmp_path))

    config.set_default_config()
    config.set("execution", "remove_unnecessary_outputs", False)

    wf = pe.Workflow("w", base_dir=Path.cwd())

    x = pe.Node(
        interface=niu.Function(
            function=totxt,
            input_names=["a", "b"],
            output_names=["c", "d"]
        ),
        name="x"
    )
    x.inputs.a = 1
    x.inputs.b = 2

    y = pe.Node(
        interface=niu.Function(
            function=select,
            input_names=["a", "b"],
            output_names=["c"]
        ),
        name="y"
    )
    wf.connect(x, "c", y, "a")
    wf.connect(x, "d", y, "b")

    z = pe.Node(
        interface=niu.Function(
            function=select,
            input_names=["a", "b"],
            output_names=["c"]
        ),
        name="z"
    )
    wf.connect(y, "c", z, "a")
    wf.connect(y, "c", z, "b")

    execgraph = wf.run(plugin=DontRunRunner())

    def get_node(name):
        for node in execgraph.nodes():
            if node.name == name:
                return node

    x = get_node("x")
    y = get_node("y")
    z = get_node("z")

    mpp = MultiProcPlugin(plugin_args=dict(keep="none"))
    mpp._generate_dependency_list(execgraph)

    rt = mpp._rt

    xrf = rt.node_resultfile_path(x)
    yrf = rt.node_resultfile_path(y)
    zrf = rt.node_resultfile_path(z)

    result = x.run()
    rt.set_node_complete(x, True)

    c = result.outputs.c
    d = result.outputs.d

    assert rt.refs[xrf] == set([yrf])
    assert rt.refs[yrf] == set([zrf])
    assert rt.refs[zrf] == set([])
    assert rt.refs[c] == set([xrf])
    assert rt.refs[d] == set([xrf])

    assert rt.deps[xrf] == set([xrf.parent, c, d])
    assert rt.deps[yrf] == set([yrf.parent, xrf])
    assert rt.deps[zrf] == set([zrf.parent, yrf])
    assert rt.deps[c] == set([xrf.parent])
    assert rt.deps[d] == set([xrf.parent])

    y.run()
    rt.set_node_complete(y, True)

    assert rt.refs[xrf] == set([])
    assert rt.refs[yrf] == set([zrf])
    assert rt.refs[zrf] == set([])
    assert rt.refs[c] == set([xrf])
    assert rt.refs[d] == set([xrf, yrf])

    assert rt.deps[xrf] == set([xrf.parent, c, d])
    assert rt.deps[yrf] == set([yrf.parent, d])
    assert rt.deps[zrf] == set([zrf.parent, yrf])
    assert rt.deps[c] == set([xrf.parent])
    assert rt.deps[d] == set([xrf.parent])

    rtc = set(rt.collect())
    assert rtc == set([xrf, c])
