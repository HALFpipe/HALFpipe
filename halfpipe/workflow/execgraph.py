# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from itertools import islice
from os import path as op

import numpy as np
import networkx as nx

import nipype.pipeline.engine as pe

from ..interface import LoadResult
from ..utils import first, hexdigest
from ..io import IndexedFile, cacheobj, uncacheobj

max_chunk_size = 50  # subjects


class DontRunRunner:
    plugin_args = dict()

    def run(*args, **kwargs):
        pass


def init_execgraph(workdir, workflow, n_chunks=None, subject_chunks=None):
    logger = logging.getLogger("halfpipe")

    uuid = workflow.uuid
    execgraph = uncacheobj(workdir, "execgraph", uuid)
    if execgraph is None:
        # create execgraph
        execgraph = workflow.run(plugin=DontRunRunner())
        execgraph.uuid = uuid
        uuidstr = str(uuid)[:8]
        logger.info(f"New execgraph: {uuidstr}")
        cacheobj(workdir, "execgraph", execgraph, uuid=uuid)

    reportjsfilename = op.join(workdir, "reports", "reportexec.js")
    allnodenames = set(node.fullname for node in execgraph.nodes())
    try:
        indexedfileobj = IndexedFile(reportjsfilename)
        assert allnodenames.issubset(indexedfileobj.file_index.indexdict.keys())
    except Exception:
        logger.info(f"Init reportexec.js")
        IndexedFile.init_indexed_js_object_file(
            reportjsfilename, "report", allnodenames, 10
        )  # TODO don't overwrite current values

    subjectworkflows = dict()
    for node in execgraph.nodes():
        subjectname = None
        if node._hierarchy.startswith("nipype.fmriprep_wf"):
            subjectname = node._hierarchy.split(".")[2]
        if subjectname is not None:
            if subjectname not in subjectworkflows:
                subjectworkflows[subjectname] = set()
            subjectworkflows[subjectname].add(node)

    if (
        subject_chunks
        or (n_chunks is not None and n_chunks > 1)
        or len(subjectworkflows) > max_chunk_size
    ):
        if n_chunks is None:
            n_chunks = -(-len(subjectworkflows) // max_chunk_size)
            logger.info(f"Will create chunks due to max_chunk_size")

        if subject_chunks:
            n_chunks = len(subjectworkflows)

        typestr = f"execgraph.{n_chunks:02d}_chunks"
        execgraphs = uncacheobj(workdir, typestr, uuid, typedisplaystr="execgraph split")
        if execgraphs is not None:
            return execgraphs

        logger.info(f"New execgraph split with {n_chunks} chunks")

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
            uhex = hexdigest(u.fullname)[:8]
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
