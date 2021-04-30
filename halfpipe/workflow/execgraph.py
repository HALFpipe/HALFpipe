# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Union

import logging
from pathlib import Path
from shutil import copyfile
import re
from collections import OrderedDict
from fnmatch import fnmatch
from argparse import Namespace
from copy import deepcopy

import networkx as nx

import nipype.pipeline.engine as pe
from nipype.pipeline.engine.utils import merge_dict

from .base import IdentifiableWorkflow
from ..interface import LoadResult
from ..utils import b32digest, resolve
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

        subject_nodes = dict()
        for node in flatgraph:
            hierarchy = node._hierarchy.split(".")
            assert len(hierarchy) >= 3
            subject_name = extract_subject_name(hierarchy)
            if subject_name is not None:
                if subject_name not in subject_nodes:
                    subject_nodes[subject_name] = set()
                subject_nodes[subject_name].add(node)

        all_subject_nodes = set.union(*subject_nodes.values())
        model_nodes = set(flatgraph.nodes) - all_subject_nodes

        # make safe load
        newnodes = dict()
        for (v, u, c) in nx.edge_boundary(flatgraph.reverse(), model_nodes, data=True):
            u.keep = True  # don't allow results to be deleted

            newu = newnodes.get(u.fullname)
            if newu is None:
                udigest = b32digest(u.fullname)[:4]
                newu = pe.Node(LoadResult(u), name=f"load_result_{udigest}", base_dir=modeldir)
                newu.config = u.config
                newnodes[u.fullname] = newu

            flatgraph.add_edge(newu, v, **c)

            newuresultfile = Path(newu.output_dir()) / f"result_{newu.name}.pklz"
            for outattr, inattr in c["connect"]:
                newu.needed_outputs = [*newu.needed_outputs, outattr]
                v.input_source[inattr] = (newuresultfile, outattr)

        logger.info("Expanding subgraphs")

        graphs = OrderedDict()

        def add_graph(s, graph):
            graph = pe.generate_expanded_graph(graph)

            for index, node in enumerate(graph):
                node.config = merge_dict(deepcopy(workflow.config), node.config)
                node.base_dir = workflow.base_dir
                node.index = index

            workflow._configure_exec_nodes(graph)

            graphs[s] = graph

        for s, nodes in sorted(subject_nodes.items(), key=lambda t: t[0]):
            s = workflow.bids_to_sub_id_map.get(s, s)

            subgraph = flatgraph.subgraph(nodes).copy()
            add_graph(s, subgraph)

        flatgraph.remove_nodes_from(all_subject_nodes)
        add_graph("model", flatgraph)

        for graph in graphs.values():
            graph.uuid = uuid

        logger.info(f'Finished graphs for workflow "{uuidstr}"')
        cacheobj(workdir, "graphs", graphs, uuid=uuid)

    return graphs
