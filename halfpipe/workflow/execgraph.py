# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from itertools import islice
from pathlib import Path

import numpy as np
import networkx as nx

import nipype.pipeline.engine as pe

from ..interface import LoadResult
from ..utils import hexdigest
from ..io import IndexedFile, DictListFile, cacheobj, uncacheobj

max_chunk_size = 50  # subjects


class DontRunRunner:
    plugin_args = dict()

    def run(*args, **kwargs):
        pass


def init_execgraph(workdir, workflow, n_chunks=None, subject_chunks=None):
    logger = logging.getLogger("halfpipe")

    uuid = workflow.uuid
    uuidstr = str(uuid)[:8]

    execgraph = uncacheobj(workdir, "execgraph", uuid)
    if execgraph is None:
        # create execgraph
        logger.info(f"Initializing new execgraph: {uuidstr}")
        execgraph = workflow.run(plugin=DontRunRunner())
        execgraph.uuid = uuid
        logger.info(f"Finished execgraph: {uuidstr}")
        cacheobj(workdir, "execgraph", execgraph, uuid=uuid)

    # init reports
    reports_directory = Path(workdir) / "reports"
    reportjsfilename = reports_directory / "reportexec.js"
    allnodenames = sorted([node.fullname for node in execgraph.nodes()])
    IndexedFile.init_indexed_js_object_file(
        reportjsfilename, "report", allnodenames, 10
    )  # TODO read current values
    for ftype in ["imgs", "vals", "preproc"]:
        preprocpath = reports_directory / f"report{ftype}.js"
        with DictListFile.cached(preprocpath) as dlf:
            dlf.is_dirty = True

    subjectworkflows = dict()
    for node in execgraph.nodes():
        subjectname = None
        hierarchy = node._hierarchy.split(".")
        if hierarchy[1] in ["fmriprep_wf", "reports_wf", "settings_wf", "features_wf"]:
            subjectname = hierarchy[2]
        if subjectname is not None:
            if subjectname not in subjectworkflows:
                subjectworkflows[subjectname] = set()
            subjectworkflows[subjectname].add(node)

    if n_chunks is None:
        n_chunks = -(-len(subjectworkflows) // max_chunk_size)

    if subject_chunks:
        n_chunks = len(subjectworkflows)

    digits = int(np.ceil(np.log10(len(subjectworkflows))))
    typestr = f"execgraph.{n_chunks:0{digits}d}_chunks"
    execgraphs = uncacheobj(workdir, typestr, uuid, typedisplaystr="execgraph split")
    if execgraphs is not None:
        return execgraphs

    logger.info(f"Initializing execgraph split with {n_chunks} chunks")

    execgraphs = []
    chunks = np.array_split(np.arange(len(subjectworkflows)), n_chunks)
    partitioniter = iter(subjectworkflows.values())
    for chunk in chunks:
        nodes = set.union(
            *islice(partitioniter, len(chunk))
        )  # take len(chunk) subjects and create union
        execgraphs.append(execgraph.subgraph(nodes).copy())

    subjectlevelnodes = set.union(*subjectworkflows.values())
    grouplevelnodes = set(execgraph.nodes()) - subjectlevelnodes
    newnodes = dict()
    for (v, u, c) in nx.edge_boundary(execgraph.reverse(), grouplevelnodes, data=True):
        newu = newnodes.get(u.fullname)
        if newu is None:
            uhex = hexdigest(u.fullname)[:8]
            newu = pe.Node(LoadResult(u), name=f"loadresult_{uhex}")
            newu.config = u.config
            newnodes[u.fullname] = newu
        execgraph.add_edge(newu, v, attr_dict=c)

    execgraph.remove_nodes_from(subjectlevelnodes)

    execgraphs.append(execgraph)
    assert len(execgraphs) == n_chunks + 1

    for execgraph in execgraphs:
        execgraph.uuid = uuid

    logger.info(f"Finished execgraph split")
    cacheobj(workdir, typestr, execgraphs, uuid=uuid)

    return execgraphs
