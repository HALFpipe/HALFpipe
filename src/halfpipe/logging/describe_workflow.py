from nipype.pipeline import engine as pe

from ..logging import logger


def describe_workflow(wf: pe.Workflow, indent: int = 0):
    pad = "    " * indent
    logger.debug(f"{pad}- WORKFLOW: {wf.name}")

    # List nodes directly in this workflow
    for node in wf._graph.nodes():
        logger.debug(f"{pad}    * Node: {node.name} ({node.__class__.__name__})")

    # List sub-workflows (workflows are treated as nodes too)
    for node in wf._graph.nodes():
        if isinstance(node, pe.Workflow):
            describe_workflow(node, indent + 1)
