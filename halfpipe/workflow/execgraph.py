# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Union, Dict

import logging
from pathlib import Path
from shutil import copyfile
import re
from collections import OrderedDict, defaultdict
from fnmatch import fnmatch
from argparse import Namespace
from copy import deepcopy

import networkx as nx

import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu
from nipype.pipeline.engine.utils import merge_dict

from ..fixes import Node
from .base import IdentifiableWorkflow
from ..utils import resolve
from ..io import DictListFile, cacheobj, uncacheobj
from ..resource import get as getresource
from .constants import constants

max_chunk_size = 50  # subjects


def filter_subject_graphs(subject_graphs: OrderedDict, opts: Namespace) -> OrderedDict:
    for pattern in opts.subject_exclude:
        subject_graphs = OrderedDict([
            (n, v)
            for n, v in subject_graphs.items()
            if not fnmatch(n, pattern)
        ])

    for pattern in opts.subject_include:
        subject_graphs = OrderedDict([
            (n, v)
            for n, v in subject_graphs.items()
            if fnmatch(n, pattern)
        ])

    if opts.subject_list is not None:
        subject_list_path = resolve(opts.subject_list, opts.fs_root)

        with open(subject_list_path, "r") as f:
            subject_set = frozenset(
                s.strip() for s in f.readlines()
            )

        subject_graphs = OrderedDict([
            (n, v)
            for n, v in subject_graphs.items()
            if n in subject_set
        ])

    return subject_graphs


def extract_subject_name(hierarchy):
    m = re.fullmatch(r"single_subject_(?P<subjectname>.+)_wf", hierarchy[2])
    if m is not None:
        return m.group("subjectname")


def find_input_source(graph: nx.DiGraph, u: Node, v: Node, c: Dict):
    stack = [
        (u, v, source_info, field) for source_info, field in c["connect"]
    ]

    result = list()

    while len(stack) > 0:
        node, v, source_info, field = stack.pop(0)
        if not isinstance(node.interface, niu.IdentityInterface):
            result.append((node, v, source_info, field))
            continue
        assert not isinstance(source_info, tuple)
        for u, _, k in graph.in_edges(node, data=True):
            for u_source_info, node_field in k["connect"]:
                if source_info == node_field:
                    stack.append(
                        (u, v, u_source_info, field)
                    )

    stack = result
    result = list()

    while len(stack) > 0:
        u, node, source_info, field = stack.pop(0)
        if not isinstance(node.interface, niu.IdentityInterface):
            result.append((u, node, source_info, field))
            continue
        for _, v, k in graph.out_edges(node, data=True):
            for node_source_info, v_field in k["connect"]:
                if node_source_info == field:
                    stack.append(
                        (u, v, source_info, v_field)
                    )

    input_source_dict = defaultdict(dict)
    for u, v, source_info, field in result:
        u.keep = True  # don't allow results to be deleted

        u._output_dir = None  # reset this just in case

        output_dir = u.output_dir()
        assert isinstance(output_dir, str)

        result_file = Path(output_dir) / f"result_{u.name}.pklz"

        input_source_dict[v][field] = (result_file, source_info)

    return input_source_dict


def init_execgraph(workdir: Union[Path, str], workflow: IdentifiableWorkflow) -> OrderedDict:
    logger = logging.getLogger("halfpipe")

    uuid = workflow.uuid
    uuidstr = str(uuid)[:8]

    # init reports

    reports_directory = Path(workdir) / "reports"
    reports_directory.mkdir(parents=True, exist_ok=True)

    indexhtml_path = reports_directory / "index.html"
    copyfile(getresource("index.html"), indexhtml_path)

    for ftype in ["imgs", "vals", "preproc", "error"]:
        report_fname = reports_directory / f"report{ftype}.js"
        with DictListFile.cached(report_fname) as dlf:
            dlf.is_dirty = True  # force write

    # init dirs

    modeldir = Path(workdir) / constants.workflowdir / "models_wf"
    modeldir.mkdir(parents=True, exist_ok=True)

    # create or load execgraph

    graphs = uncacheobj(workdir, "graphs", uuid)
    if graphs is None:
        logger.info(f'Initializing execution graph for workflow "{uuidstr}"')

        workflow._generate_flatgraph()
        flatgraph = workflow._graph

        workflow._set_needed_outputs(flatgraph)

        logger.info("Splitting graph")

        subject_nodes = defaultdict(set)
        for node in flatgraph:
            node.base_dir = workflow.base_dir  # make sure to use correct base path

            hierarchy = node._hierarchy.split(".")
            assert len(hierarchy) >= 3
            subject_name = extract_subject_name(hierarchy)
            if subject_name is not None:
                subject_nodes[subject_name].add(node)

        all_subject_nodes = set.union(*subject_nodes.values())
        model_nodes = set(flatgraph.nodes) - all_subject_nodes

        input_source_dict = defaultdict(dict)
        for (v, u, c) in nx.edge_boundary(flatgraph.reverse(), model_nodes, data=True):
            edge_input_source_dict = find_input_source(flatgraph, u, v, c)

            for v, input_sources in edge_input_source_dict.items():
                input_source_dict[v].update(input_sources)

        logger.info("Expanding subgraphs")

        graphs = OrderedDict()

        def add_graph(s, graph):
            graph = pe.generate_expanded_graph(graph)

            for index, node in enumerate(graph):
                node.config = merge_dict(deepcopy(workflow.config), node.config)
                node.base_dir = workflow.base_dir
                node.index = index

            workflow._configure_exec_nodes(graph)

            for node in graph:
                if node in input_source_dict:
                    node.input_source.update(input_source_dict[node])

            graphs[s] = graph

        for s, nodes in sorted(subject_nodes.items(), key=lambda t: t[0]):
            s = workflow.bids_to_sub_id_map.get(s, s)

            subgraph = flatgraph.subgraph(nodes).copy()
            add_graph(s, subgraph)

        flatgraph.remove_nodes_from(all_subject_nodes)
        if len(flatgraph.nodes) > 0:
            add_graph("model", flatgraph)

        for graph in graphs.values():
            graph.uuid = uuid

        logger.info(f'Finished graphs for workflow "{uuidstr}"')
        cacheobj(workdir, "graphs", graphs, uuid=uuid)

    return graphs
