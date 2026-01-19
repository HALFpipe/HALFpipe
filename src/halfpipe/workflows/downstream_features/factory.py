# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from collections import defaultdict

from nipype.pipeline import engine as pe

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

        # filled in by .create()
        self.hierarchies: dict[str, list[list[pe.Workflow]]] = defaultdict(list)

    # TODO leaving this format to match other factories, but should be renamed _setup and made internal to init
    def setup(self):
        # modelled of stats factory, not worried about source_files & processing_groups bc going to do a group level anaylsis
        for downstream_feature in self.ctx.spec.downstream_features:
            self._create(downstream_feature)

    def _create(
        self,
        downstream_feature,
    ) -> pe.Workflow | None:
        """Creates a downstream_feature workflow and connects it with HALFpipe."""
        hierarchy = self._create_hierarchy("downstream_feature_wf")  # = [self.ctx.workflow, downstream_feature_wf]
        parent_workflow = hierarchy[-1]  # = downstream_feature_wf (empty wf w/ name)

        # Prepare/load files necessary for type of feature workflow & create worklow
        # Necessary for anything in spec file that is a path/pointer
        if downstream_feature.type == "gradients":
            # TODO test/validate
            # check if atlas_based_connectivity was run
            if "atlas_based_connectivity" not in [feature.type for feature in self.ctx.spec.features]:
                raise RuntimeError("Gradients are calculated on atlas_based_connectivity matrices.")

            workflow = init_gradients_wf(
                downstream_feature=downstream_feature,
                workdir=str(self.ctx.workdir),
                # TODO memcalc? stats factory doesn't have
            )

        else:
            raise ValueError(f'Unknown downstream_feature type "{downstream_feature.type}"')

        # TODO taken directly from stats factory but list of list is confusing (see comments there)
        # add workflow to larger halfpipe workflow
        parent_workflow.add_nodes([workflow])
        hierarchy.append(workflow)
        # = [outer_workflow, downstream_feature_wf, gradients_wf]

        if downstream_feature.name not in self.hierarchies:
            self.hierarchies[downstream_feature.name] = []
        self.hierarchies[downstream_feature.name].append(hierarchy)

        # TODO written for current case where only downstream feature is gradients might need to be modified in the future
        # TODO find out what this actually is!
        input_feature_name = "atlas_based_connectivity_wf"
        input_hierarchy = self.feature_factory.get_hierarchy(input_feature_name)
        self.connect_attr(
            input_hierarchy,  # should be a hierarchy
            "outputnode",
            "resultdicts",
            hierarchy,  # [self.ctx.workflow, stats_wf, workflow]
            "inputnode",
            "in1",
        )

        return workflow

    def get_hierarchy(
        self,
        downstream_feature_name: str,
    ) -> list[list[pe.Workflow]]:
        """Returns the hierarchy associated with the given downstream feature name."""
        return self.hierarchies[downstream_feature_name]

    # TODO Needs to be implemented for gradients?
    def connect(self, *args, **kwargs):
        raise NotImplementedError()
