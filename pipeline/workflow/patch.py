# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from copy import deepcopy

from fmriprep.interfaces.bids import DerivativesDataSink

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

import networkx as nx

from .fake import (
    FakeBIDSLayout,
    FakeDerivativesDataSink
)

# def _get_all_workflows(wf):
#     workflows = [wf]
#     for node in wf._graph.nodes():
#         if isinstance(node, pe.Workflow):
#             workflows.extend(_get_all_workflows(node))
#     return workflows

G = nx.DiGraph()
G.add_edge("A","C")
G.add_edge("B","C")
G.add_edge("C","G")
G.add_edge("G","H")
G.add_edge("C","D")
G.add_edge("D","E")
G.add_edge("D","F")
G.add_edge("E","I")
G.add_edge("F","I")
G.add_edge("I","J")

def _rank_collapse(graph):
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
                if graph.in_degree(child) == 1 and graph.out_degree(child) == 1:
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
        fmriprep_reportlets_dir, fmriprep_output_dir):
    workflow._graph = workflow._create_flat_graph()
        
    # workflows = _get_all_workflows(workflow)       

    # for wf in workflows:
    for _, _, d in workflow._graph.edges(data = True):
        for i, (src, dest) in enumerate(d["connect"]):
            if isinstance(src, tuple) and len(src) > 1:
                if "fix_multi_T1w_source_name" in src[1]:
                    d["connect"][i] = (src[0], dest)

    for node in workflow._get_all_nodes():
        if type(node._interface) is DerivativesDataSink:
            base_directory = node._interface.inputs.base_directory
            in_file = node._interface.inputs.in_file
            source_file = node._interface.inputs.source_file
            suffix = node._interface.inputs.suffix
            extra_values = node._interface.inputs.extra_values
            node._interface = FakeDerivativesDataSink(images = images, 
                    fmriprep_reportlets_dir = fmriprep_reportlets_dir, 
                    fmriprep_output_dir = fmriprep_output_dir,
                    node_id = "%s.%s" % (node._hierarchy, node.name), depends = None,
                base_directory = base_directory,
                source_file = source_file,
                in_file = in_file,
                suffix = suffix,
                extra_values = extra_values)
        elif type(node._interface) is niu.Function and \
            "fix_multi_T1w_source_name" in node._interface.inputs.function_str:
            node._interface.inputs.function_str = "def fix_multi_T1w_source_name(in_files):\n    if isinstance(in_files, str):\n        return in_files\n    else:\n        return in_files[0]"
                
    for node in workflow._get_all_nodes():
        node.config = deepcopy(workflow.config)
    
    return workflow

