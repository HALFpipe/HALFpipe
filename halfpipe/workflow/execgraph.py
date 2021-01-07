# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from itertools import islice
from pathlib import Path
from shutil import copyfile

import numpy as np
import networkx as nx

import nipype.pipeline.engine as pe

from ..interface import LoadResult
from ..utils import b32digest
from ..io import DictListFile, cacheobj, uncacheobj
from ..resource import get as getresource
from .constants import constants

max_chunk_size = 50  # subjects


class DontRunRunner:
    plugin_args = dict()

    def run(self, *args, **kwargs):
        pass


def init_execgraph(workdir, workflow, n_chunks=None, subject_chunks=None):
    logger = logging.getLogger("halfpipe")

    uuid = workflow.uuid
    uuidstr = str(uuid)[:8]

    # create or load execgraph

    execgraph = uncacheobj(workdir, "execgraph", uuid)
    if execgraph is None:
        logger.info(f"Initializing new execgraph {uuidstr}")
        execgraph = workflow.run(plugin=DontRunRunner())
        execgraph.uuid = uuid
        logger.info(f"Finished execgraph {uuidstr}")
        cacheobj(workdir, "execgraph", execgraph, uuid=uuid)

    # init reports

    reports_directory = Path(workdir) / "reports"
    reports_directory.mkdir(parents=True, exist_ok=True)

    indexhtml_path = reports_directory / "index.html"
    copyfile(getresource("index.html"), indexhtml_path)

    for ftype in ["imgs", "vals", "preproc", "error"]:
        report_fname = reports_directory / f"report{ftype}.js"
        with DictListFile.cached(report_fname) as dlf:
            dlf.is_dirty = True  # force write

    # split workflow

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

    typestr = f"execgraph.{n_chunks:d}_chunks"
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

    # make safe load
    subjectlevelnodes = set.union(*subjectworkflows.values())
    modelnodes = set(execgraph.nodes()) - subjectlevelnodes

    modeldir = Path(workdir) / constants.workflowdir / "models_wf"
    modeldir.mkdir(parents=True, exist_ok=True)

    newnodes = dict()
    for (v, u, c) in nx.edge_boundary(execgraph.reverse(), modelnodes, data=True):
        u.keep = True  # don't allow results to be deleted

        newu = newnodes.get(u.fullname)
        if newu is None:
            udigest = b32digest(u.fullname)[:4]
            newu = pe.Node(LoadResult(u), name=f"load_result_{udigest}", base_dir=modeldir)
            newu.config = u.config
            newnodes[u.fullname] = newu

        execgraph.add_edge(newu, v, attr_dict=c)

        newuresultfile = Path(newu.output_dir()) / f"result_{newu.name}.pklz"
        for outattr, inattr in c["connect"]:
            newu.needed_outputs = [*newu.needed_outputs, outattr]
            v.input_source[inattr] = (newuresultfile, outattr)

    execgraph.remove_nodes_from(subjectlevelnodes)

    execgraphs.append(execgraph)
    assert len(execgraphs) == n_chunks + 1

    for execgraph in execgraphs:
        execgraph.uuid = uuid

    logger.info("Finished execgraph split")
    cacheobj(workdir, typestr, execgraphs, uuid=uuid)

    return execgraphs
