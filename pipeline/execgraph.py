# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from itertools import islice

import numpy as np
import networkx as nx

from .utils import cacheobj, uncacheobj


class DontRunRunner:
    plugin_args = dict()

    def run(*args, **kwargs):
        pass


def init_execgraph(workdir, workflow, n_chunks=None):
    logger = logging.getLogger("pipeline")

    uuid = workflow.uuid
    execgraphs = uncacheobj(workdir, "execgraph", uuid)
    if execgraphs is not None:
        return execgraphs

    # create execgraph
    execgraph = workflow.run(plugin=DontRunRunner())
    execgraph.uuid = uuid
    uuidstr = str(uuid)[:8]
    logger.info(f"New execgraph: {uuidstr}")

    if n_chunks is None or n_chunks <= 1:
        execgraphs = (execgraph,)
    else:
        execgraphs = []

        subjectworkflows = {}
        grouplevelnodes = set()
        for node in execgraph.nodes():
            if node._hierarchy.startswith("nipype.subjectlevel"):
                subjectworkflowname = node._hierarchy.split(".")[2]
                if subjectworkflowname not in subjectworkflows:
                    subjectworkflows[subjectworkflowname] = set()
                subjectworkflows[subjectworkflowname].add(node)
            else:
                grouplevelnodes.add(node)

        chunks = np.array_split(np.arange(len(subjectworkflows)), n_chunks)
        partitioniter = iter(subjectworkflows.values())
        for chunk in chunks:
            nodes = set.union(*islice(partitioniter, len(chunk)))
            execgraphs.append(execgraph.subgraph(nodes))

        subjectlevelnodes = set.union(*subjectworkflows.values())
        for (u, v, c) in nx.edge_boundary(execgraph, subjectlevelnodes, data=True):
            import pdb

            pdb.set_trace()

    cacheobj(workdir, "execgraph", execgraphs, uuid=uuid)
    return execgraphs
