# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from collections import defaultdict

from nipype.pipeline import engine as pe

from halfpipe.logging import logger
from halfpipe.workflows.downstream_features.gradients import init_gradients_wf
from halfpipe.workflows.factory import Factory, FactoryContext
from halfpipe.workflows.features.factory import FeatureFactory


inputnode_name = re.compile(r"(?P<prefix>[a-z]+_)?inputnode")


class DownstreamFeatureFactory(Factory):
    """Class is reponsible for connecting downstream feature workflows up into rest of halfpipe."""
    def __init__(
        self,
        ctx: FactoryContext,
        feature_factory: FeatureFactory,
        ) -> None:
        super().__init__(ctx)

        self.feature_factory = feature_factory
        # TODO self.processing_groups ?

        # TODO do we need any source_files? gradient ref?
        # TODO clarify difference between raw sources dict as a list of subjects/bold files vs actual source files we would need ie gradient ref

        # filled in by .create()
        self.hierarchies: dict[str, list[list[pe.Workflow]]] = defaultdict(list)
    
    def setup(
        self, 
        raw_sources_dict: dict | None = None, # TODO ?
        processing_groups = None, # TODO ?
        ):
        # TODO ?
        logger.debug(f"DownstreamFeatureFactory->setup-> raw_sources_dict: {raw_sources_dict},processing_groups: {processing_groups}")
        # TODO dont understand this for now
        # pass processing_groups also here so that when later _get_hierarchy is used in create, the processing_groups can
        # there so that the right workflow can be found
        self.processing_groups = processing_groups
        raw_sources_dict = dict() if raw_sources_dict is None else raw_sources_dict

        for downstream_feature in self.ctx.spec.downstream_features:
            logger.info(f"DownstreamFeatureFactory->setup-> downstream_feature: {downstream_feature}")
            source_files = set(raw_sources_dict.keys())
            logger.info(f"DownstreamFeatureFactory->setup-> source_files: {source_files}")

            self.create(downstream_feature)

    def create(
        self,
        downstream_feature,
        ) -> pe.Workflow | None:
        """Creates a downstream_feature workflow and connects it with HALFpipe."""

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

        self.hierarchies[downstream_feature.name].append(hierarchy)

        # TODO refactor
        for node in workflow._graph.nodes:
            m = inputnode_name.fullmatch(node.name)
            # only runs for input nodes
            if m is not None:
                # want to find hierarchy from feature_factory that matches

                # TODO this doesn't make sense bc we need the specific hierarchy from the atlas_based_connectivity_wf
                # hard code connections like fmriprep factory?
                self.feature_factory.connect(hierarchy, node)

        return workflow
    
    def get(
        self,
        downstream_feature_name: str,
        # ) -> list[list[pe.Workflow]]:
        ):
        # TODO a docstring or logic for why this is here
        # ie what is get supposed to do in other factories & why it shouldnt be implemented
        hierarchy = self.hierarchies[downstream_feature_name]
        outputnode = hierarchy[-1].get_node("outputnode")
        return hierarchy, outputnode

    # TODO Needs to be implemented for gradients?
    def connect(self, *args, **kwargs):
        raise NotImplementedError()
