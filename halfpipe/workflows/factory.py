# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import ABC, abstractmethod

from nipype.pipeline import engine as pe

from fmriprep.workflows.bold.base import _get_wf_name

from ..utils.format import format_like_bids


class FactoryContext:
    def __init__(self, workdir, spec, bidsdatabase, workflow):
        self.workdir = workdir
        self.spec = spec
        self.database = bidsdatabase.database
        self.bidsdatabase = bidsdatabase
        self.workflow = workflow


class Factory(ABC):
    def __init__(self, ctx):
        self.workdir = ctx.workdir
        self.spec = ctx.spec
        self.database = ctx.database
        self.bidsdatabase = ctx.bidsdatabase
        self.workflow = ctx.workflow

    def _endpoint(self, hierarchy, node, attr):
        if len(hierarchy) > 1:
            parent = hierarchy[1]
            fullattr = ".".join([*[wf.name for wf in hierarchy[2:]], node.name, attr])
            return parent, fullattr
        return node, attr

    def _single_subject_wf_name(self, sourcefile=None, bids_subject_id=None, subject_id=None):
        bidsdatabase = self.bidsdatabase
        if bids_subject_id is None:
            if sourcefile is not None:
                bidspath = bidsdatabase.tobids(sourcefile)
                subject_id = bidsdatabase.tagval(bidspath, "subject")
            if subject_id is not None:
                bids_subject_id = format_like_bids(subject_id)
        if bids_subject_id is not None:
            return "single_subject_%s_wf" % bids_subject_id

    def _bold_wf_name(self, sourcefile):
        bidspath = self.bidsdatabase.tobids(sourcefile)
        return _get_wf_name(bidspath)

    def _get_hierarchy(self, name, sourcefile=None, subject_id=None, childname=None, create_ok=True):
        hierarchy = [self.workflow]

        def require_workflow(child_name):
            wf = hierarchy[-1]
            child = wf.get_node(child_name)
            if child is None:
                assert create_ok
                child = pe.Workflow(name=child_name)
                wf.add_nodes([child])
            hierarchy.append(child)

        require_workflow(name)

        single_subject_wf_name = self._single_subject_wf_name(sourcefile=sourcefile, subject_id=subject_id)

        if single_subject_wf_name is not None:
            require_workflow(single_subject_wf_name)

        if sourcefile is not None:
            if self.database.tagval(sourcefile, "datatype") == "func":
                require_workflow(self._bold_wf_name(sourcefile))

        if childname is not None:
            require_workflow(childname)

        return hierarchy

    @abstractmethod
    def get(self, *args, **kwargs):
        raise NotImplementedError()

    def connect_common_attrs(self, outputhierarchy, outputnode, inputhierarchy, inputnode):
        if isinstance(outputnode, str):
            outputnode = outputhierarchy[-1].get_node(outputnode)
        if isinstance(inputnode, str):
            inputnode = inputhierarchy[-1].get_node(inputnode)

        inputattrs = set(inputnode.inputs.copyable_trait_names())
        outputattrs = set(outputnode.outputs.copyable_trait_names())
        attrs = inputattrs & outputattrs  # find common attr names

        for attr in attrs:
            self.connect_attr(outputhierarchy, outputnode, attr, inputhierarchy, inputnode, attr)
        return attrs

    def connect_attr(self, outputhierarchy, outputnode, outattr, inputhierarchy, inputnode, inattr):
        inputhierarchy = [*inputhierarchy]  # make copies
        outputhierarchy = [*outputhierarchy]

        assert outputhierarchy[0] == inputhierarchy[0]
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
        workflow.connect(*outputendpoint, *inputendpoint)

    def connect(self, nodehierarchy, node, *args, **kwargs):
        outputhierarchy, outputnode = self.get(*args, **kwargs)
        self.connect_common_attrs(outputhierarchy, outputnode, nodehierarchy, node)
