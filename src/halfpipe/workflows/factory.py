# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from fmriprep.workflows.bold.base import _get_wf_name
from nipype.pipeline import engine as pe

from ..fixes.workflows import IdentifiableWorkflow
from ..ingest.bids import BidsDatabase
from ..ingest.database import Database
from ..logging import logger
from ..model.spec import Spec
from ..utils.format import format_like_bids


@dataclass
class FactoryContext:
    workdir: Path
    spec: Spec
    database: Database
    bids_database: BidsDatabase
    workflow: IdentifiableWorkflow


class Factory(ABC):
    def __init__(
        self, 
        ctx: FactoryContext,
        ):
        self.ctx = ctx

    def _endpoint(self, hierarchy, node, attr):
        if len(hierarchy) > 1:
            parent = hierarchy[1]
            fullattr = ".".join([*[wf.name for wf in hierarchy[2:]], node.name, attr])
            return parent, fullattr
        return node, attr

    def _single_subject_wf_name(
        self,
        source_file: Path | str | None = None,
        bids_subject_id: str | None = None,
        subject_id: str | None = None,
    ) -> str | None:
        """ Formats a wf name based on source file and bids & subject id."""
        bids_database = self.ctx.bids_database

        if bids_subject_id is None:
            if source_file is not None:
                bids_path = bids_database.to_bids(str(source_file))
                assert bids_path is not None
                subject_id = bids_database.get_tag_value(bids_path, "subject")
            if subject_id is not None:
                bids_subject_id = format_like_bids(subject_id)

        if bids_subject_id is not None:
            # the naming has changed from single_subject_% to sub_% in fmriprep24
            return f"sub_{bids_subject_id}_wf"

        return None

    def _bold_wf_name(self, source_file: Path | str) -> str:
        # Implementation by fmriprep requires passing a prefix since that is what fmriprep preprends to the bold workflows:
        # https://github.com/nipreps/fmriprep/blob/73189de5ee576ffc73ab432b7419304d44ce5776/fmriprep/workflows/bold/base.py#L195
        bidspath = self.ctx.bids_database.to_bids(str(source_file))
        return _get_wf_name(bidspath, "bold")

    def _get_hierarchy(
        self,
        name: str,
        source_file: Path | str | None = None,
        subject_id: str | None = None,
        childname: str | None = None,
        create_ok: bool = True,
    ):
        """
        Retrieve or create a hierarchy of workflows.
        This method builds a list of workflows starting from the main workflow in
        the context (`ctx.workflow`), adding sub-workflows as needed based on the
        `name`, `source_file`, `subject_id`, and `childname` arguments. It ensures
        that each workflow exists, creating them if allowed (`create_ok=True`).
        """
        # TODO i dont understand this function at all it seems like its just adding blank workflows, never calling init_(appropriate wf name)_wf

        hierarchy: list[pe.Workflow] = [self.ctx.workflow]

        # TODO this function seems unnecessary/refactor
        def require_workflow(
            child_name: str,
            ):
            """ Checks if child_name is in workflow, if not it is added."""
            # workflow is last in hierarchy list
            workflow = hierarchy[-1]
            child = workflow.get_node(child_name)

            if child is None:
                if create_ok is False:
                    # TODO make the error informative
                    raise ValueError()
                
                # This seems bizarre, just creating any workflow w/ correct name?
                child = pe.Workflow(name=child_name)
                # Will this new workflow have any nodes?
                workflow.add_nodes([child])

            assert isinstance(child, pe.Workflow)

            # add newest workflow to end of hierarchy list
            hierarchy.append(child)

        # eg on first call to create in setup of stats py this will create a blank workflow called stats_wf
        require_workflow(name)

        # get the correct name formatted or None
        single_subject_wf_name = self._single_subject_wf_name(source_file=source_file, subject_id=subject_id)

        if single_subject_wf_name is not None:
            # adds a blank wf called single subject wf name to hierarchy
            require_workflow(single_subject_wf_name)

        if source_file is not None:
            if self.ctx.database.tagval(source_file, "datatype") == "func":
                # adds a blank wf called bold wf name to hierarchy
                require_workflow(self._bold_wf_name(source_file))

        if childname is not None:
            # adds a blank wf called childname to hierarchy
            require_workflow(childname)

        return hierarchy

    @abstractmethod
    def get(self, *args, **kwargs):
        raise NotImplementedError()

    def connect_attr(
        self, 
        outputhierarchy, 
        outputnode, 
        outattr, 
        inputhierarchy, 
        inputnode, 
        inattr
        ):
        inputhierarchy = [*inputhierarchy]  # make copies
        outputhierarchy = [*outputhierarchy]

        # The first element of both hierarchies needs to be the same
        if outputhierarchy[0] != inputhierarchy[0]:
            raise ValueError(f"Cannot connect {outputhierarchy} to {inputhierarchy}")

        # removes all but last common element
        while outputhierarchy[1] == inputhierarchy[1]:
            inputhierarchy.pop(0)
            outputhierarchy.pop(0)

        workflow = inputhierarchy[0]

        if isinstance(outputnode, str):
            outputnode = outputhierarchy[-1].get_node(outputnode)
        if isinstance(inputnode, str):
            inputnode = inputhierarchy[-1].get_node(inputnode)

        outputendpoint = self._endpoint(outputhierarchy, outputnode, outattr)
        inputendpoint = self._endpoint(inputhierarchy, inputnode, inattr)

        logger.debug(
            f"Connecting output '{outattr}' from node '{outputnode.fullname}' "
            f"to input '{inattr}' of node '{inputnode.fullname}'"
        )
        workflow.connect(*outputendpoint, *inputendpoint)

    def connect_common_attrs(
        self, 
        outputhierarchy, 
        outputnode, 
        inputhierarchy, 
        inputnode
        ) -> set[str]:
        """ Connects workflows together based on commonly named attributes of output & input nodes. """

        if isinstance(outputnode, str):
            outputnode = outputhierarchy[-1].get_node(outputnode)
        if isinstance(inputnode, str):
            inputnode = inputhierarchy[-1].get_node(inputnode)

        inputattrs = set(inputnode.inputs.copyable_trait_names())
        outputattrs = set(outputnode.outputs.copyable_trait_names())
        # common attr names
        attrs = inputattrs & outputattrs

        for attr in attrs:
            self.connect_attr(outputhierarchy, outputnode, attr, inputhierarchy, inputnode, attr)
        return attrs

    def connect(
        self, 
        nodehierarchy, 
        node, 
        *args, 
        **kwargs
        ) -> set[str]:
        # get is implemented by subclasses
        outputhierarchy, outputnode = self.get(*args, **kwargs)
        return self.connect_common_attrs(outputhierarchy, outputnode, nodehierarchy, node)
