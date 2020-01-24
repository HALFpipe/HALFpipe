# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys

import networkx as nx

from copy import deepcopy

from niworkflows.interfaces.bids import DerivativesDataSink
from nipype.interfaces import utility as niu

from .fake import FakeDerivativesDataSink

G = nx.DiGraph()
G.add_edge("A", "C")
G.add_edge("B", "C")
G.add_edge("C", "G")
G.add_edge("G", "H")
G.add_edge("C", "D")
G.add_edge("D", "E")
G.add_edge("D", "F")
G.add_edge("E", "I")
G.add_edge("F", "I")
G.add_edge("I", "J")


def _rank_collapse(graph):
    """
    currently unused, ranks nodes of graph by order of execution

    :param graph: the graph

    """
    indegree_map = {v: d for v, d in graph.in_degree() if d > 0}
    # These nodes have zero indegree and ready to be returned.
    zero_indegree = [v for v, d in graph.in_degree() if d == 0]

    ranks = {}

    i = 0
    while zero_indegree:
        next_zero_indegree = []
        for node in zero_indegree:
            ranks[node] = i
            for _, child in graph.out_edges(node):
                if graph.in_degree(child) == 1 and \
                        graph.out_degree(child) == 1:
                    _, child_ = next(iter(graph.out_edges(child)))
                    if graph.in_degree(child_) == 1:
                        child = child_
                indegree_map[child] -= 1
                if indegree_map[child] == 0:
                    next_zero_indegree.append(child)
                    del indegree_map[child]

        i += 1
        zero_indegree = next_zero_indegree

    return ranks


def patch_wf(workflow, images,
             output_dir, fmriprep_reportlets_dir, fmriprep_output_dir):
    """
    patches/edits the FMRIPREP-generated workflow so that BIDS-specific
    nodes are replaced with generic nodes

    :param workflow: workflow to patch
    :param images: the images data structure as specified in pipeline.json
    :param output_dir: the output dir used for custom pipeline outputs
    :param fmriprep_reportlets_dir: the reportlets dir passed to FMRIPREP
    :param fmriprep_output_dir: the output dir passed to FMRIPREP

    """
    workflow._graph = workflow._create_flat_graph()

    # fmriprep includes a bugfix for when multiple T1w images are passed,
    # so that only one is used for functional preprocessing. This can be the
    # the case in longitudinal studies.
    # However, as this function depends on BIDS, and because we don't support
    # longitudinal data in the first place, we attempt to remove this bugfix.
    for _, _, d in workflow._graph.edges(data=True):
        for i, (src, dest) in enumerate(d["connect"]):
            if isinstance(src, tuple) and len(src) > 1:
                if "fix_multi_T1w_source_name" in src[1]:
                    d["connect"][i] = (src[0], dest)

    for node in workflow._get_all_nodes():
        if isinstance(node.interface, DerivativesDataSink):
            # the DerivativesDataSink class of fmriprep depends on the BIDS
            # data structure to determine output file names. We replace it with
            # a custom version that does not, this class is called
            # FakeDerivativesDataSink.
            node_id = "%s.%s" % (node._hierarchy, node.name)
            sys.stdout.write(
                "Patching DerivativesDataSink {}\n".format(node_id))
            node._interface = FakeDerivativesDataSink(
                images=images,
                output_dir=output_dir,
                fmriprep_reportlets_dir=fmriprep_reportlets_dir,
                fmriprep_output_dir=fmriprep_output_dir,
                node_id=node_id, depends=None,

                base_directory=node.inputs.base_directory,
                source_file=node.inputs.source_file,
                in_file=node.inputs.in_file,
                suffix=node.inputs.suffix,
                extra_values=node.inputs.extra_values,
                keep_dtype=node.inputs.keep_dtype,
                space=node.inputs.space,
                check_hdr=node.inputs.check_hdr,
                compress=node.inputs.compress
            )
        elif isinstance(node.interface, niu.Function):
            if "fix_multi_T1w_source_name" in \
                    node.interface.inputs.function_str:
                # patch function nodes with fix_multi_T1w_source_name
                node.interface.inputs.function_str = \
                    "def fix_multi_T1w_source_name(in_files):\n" + \
                    "    if isinstance(in_files, str):\n" + \
                    "        return in_files\n" + \
                    "    else:\n" + \
                    "        return in_files[0]"
            elif "_bids_relative" in \
                    node.interface.inputs.function_str:
                # patch function nodes with _bids_relative
                node.interface.inputs.function_str = \
                    "def _bids_relative(in_files, bids_root):\n" + \
                    "    return in_files"

    # copy run configuration of root workflow to nodes
    for node in workflow._get_all_nodes():
        node.config = deepcopy(workflow.config)

    return workflow
