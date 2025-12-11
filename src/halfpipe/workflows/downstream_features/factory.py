# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from collections import defaultdict
from typing import Any

from nipype.pipeline import engine as pe

from ...collect.events import collect_events
from ...collect.metadata import collect_metadata
from ...logging import logger
from ...model.downstream_feature import DownstreamFeatureSchema
from ...model.spec import Spec
from ..factory import Factory, FactoryContext
from ..memory import MemoryCalculator
from ..features.factory import FeatureFactory

from ..downstream_features.gradients import init_gradients_wf

inputnode_name = re.compile(r"(?P<prefix>[a-z]+_)?inputnode")

class DownstreamFeatureFactory(Factory):
    """ Class is reponsible for connecting downstream feature workflows up into rest of halfpipe."""
    # ALL ADAPTED FROM FEATURE FACTORY NOT TESTED
    def __init__(
        self, 
        ctx: FactoryContext, 
        feature_factory: FeatureFactory,
        ) -> None:

        super().__init__(ctx)

        self.feature_factory = feature_factory

        # TODO do we need any source_files?

        # filled in by .create()
        self.workflows: dict[str, list[list[pe.Workflow]]] = defaultdict(list)
    
    def get(
        self, 
        downstream_feature_name: str, 
        #) -> list[list[pe.Workflow]]:
        ):
        # TODO a docstring or logic for why this is here
        # ie what is get supposed to do in other factories & why it shouldnt be implemented
        hierarchy = self.workflows[downstream_feature_name]
        outputnode = hierarchy[-1].get_node("outputnode")
        return hierarchy, outputnode

    def create(
        self, 
        downstream_feature,
        ) -> pe.Workflow | None:
        """ Creates a downstream_feature workflow and connects it with HALFpipe."""

        hierarchy = self._get_hierarchy("downstream_feature_wf")
        # = [outer_workflow, downstream_feature_wf]
        parent_workflow = hierarchy[-1]

        # Prepare/load files necessary for type of feature workflow & create worklow
        # Necessary for anything in spec file that is a path/pointer
        if downstream_feature.type == "gradients":
            # TODO gradient reference

            workflow = init_gradients_wf(
                downstream_feature=downstream_feature,
                workdir=str(self.ctx.workdir),
                # TODO memcalc?
            )

        else:
            raise ValueError(f'Unknown downstream_feature type "{downstream_feature.type}"')

        # add workflow to larger halfpipe workflow
        parent_workflow.add_nodes([workflow])
        hierarchy.append(workflow)
        # = [outer_workflow, downstream_feature_wf, gradients_wf]

        self.workflows[downstream_feature.name].append(hierarchy)

        # TODO refactor
        for node in workflow._graph.nodes:
            m = inputnode_name.fullmatch(node.name)
            # only runs for input nodes
            if m is not None:
                # want to find hierarchy from feature_factory that matches

                # TODO this doesn't make sense bc we need the specific hierarchy from the atlas_based_connectivity_wf
                # hard code connections like fmriprep factory?
                self.feature_factory.connect(
                    hierarchy, 
                    node
                )

        return workflow
    
    def setup(self, raw_sources_dict: dict | None = None):
        # TODO do we need any raw sources?
        # gradients ref file?

        for downstream_feature in self.ctx.spec.downstream_features:
            self.create(downstream_feature)

    # TODO Needs to be implemented for gradients?
    def connect(self, *args, **kwargs):
        raise NotImplementedError()