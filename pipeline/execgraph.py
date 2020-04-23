# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from itertools import islice
from os import path as op

import numpy as np
import networkx as nx

import nipype.pipeline.engine as pe

from .interface import LoadResult
from .utils import cacheobj, uncacheobj, first, hexdigest
from .io import init_indexed_js_object_file, IndexedFile


class DontRunRunner:
    plugin_args = dict()

    def run(*args, **kwargs):
        pass


def init_execgraph(workdir, workflow, n_chunks=None):
    logger = logging.getLogger("pipeline")

    uuid = workflow.uuid
    execgraph = uncacheobj(workdir, "execgraph", uuid)
    if execgraph is None:
        # create execgraph
        execgraph = workflow.run(plugin=DontRunRunner())
        execgraph.uuid = uuid
        uuidstr = str(uuid)[:8]
        logger.info(f"New execgraph: {uuidstr}")
        cacheobj(workdir, "execgraph", execgraph, uuid=uuid)

    reportjsfilename = op.join(workdir, "reports", "execreport.js")
    try:
        IndexedFile(reportjsfilename)
    except Exception:
        logger.info(f"Init execreport.js")
        allnodenames = [node.fullname for node in execgraph.nodes()]
        init_indexed_js_object_file(
            reportjsfilename, "qualitycheck.execreport", allnodenames, 10
        )

    if n_chunks is not None and n_chunks > 1:
        typestr = f"execgraph.{n_chunks:02d}_chunks"
        execgraphs = uncacheobj(workdir, typestr, uuid, typedisplaystr="execgraph split")
        if execgraphs is not None:
            return execgraphs

        logger.info(f"New execgraph split with {n_chunks} chunks")
        subjectworkflows = dict()
        for node in execgraph.nodes():
            if node._hierarchy.startswith("nipype.subjectlevel"):
                subjectworkflowname = node._hierarchy.split(".")[2]
                if subjectworkflowname not in subjectworkflows:
                    subjectworkflows[subjectworkflowname] = set()
                subjectworkflows[subjectworkflowname].add(node)

        execgraphs = []
        chunks = np.array_split(np.arange(len(subjectworkflows)), n_chunks)
        partitioniter = iter(subjectworkflows.values())
        for chunk in chunks:
            nodes = set.union(
                *islice(partitioniter, len(chunk))
            )  # take len(chunk) subjects and create union
            execgraphs.append(execgraph.subgraph(nodes).copy())

        subjectlevelnodes = set.union(*subjectworkflows.values())
        for (u, v, c) in nx.edge_boundary(execgraph, subjectlevelnodes, data=True):
            attrs = [first(inattr) for inattr, outattr in c["connect"]]
            uhex = hexdigest(u.fullname)
            newu = pe.Node(LoadResult(u, attrs), name=f"loadresult_{uhex}")
            newu.config = u.config
            execgraph.remove_node(u)
            execgraph.add_edge(newu, v, attr_dict=c)
        execgraph.remove_nodes_from(subjectlevelnodes)

        execgraphs.append(execgraph)
        assert len(execgraphs) == n_chunks + 1
        cacheobj(workdir, typestr, execgraphs, uuid=uuid)

        return execgraphs
    else:
        return [execgraph]
