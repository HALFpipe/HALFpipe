# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re

from ...logging import logger
from ..factory import Factory
from ..features.factory import FeatureFactory
from .base import init_stats_wf

inputnode_name = re.compile(r"(?P<prefix>[a-z]+_)?inputnode")


class StatsFactory(Factory):
    def __init__(
        self,
        ctx,
        feature_factory: FeatureFactory,
    ) -> None:
        super().__init__(ctx)

        self.feature_factory = feature_factory
        # TODO should standardize, here its a dict whereas its a list in other factories
        self.hierarchies = dict()
    
    # TODO rename to _setup and made internal to init
    def setup(self):
        for model in self.ctx.spec.models:
            self.create(model)

    # TODO rename to _create
    def create(
        self, 
        model
        ):
        hierarchy = self._create_hierarchy("stats_wf") # = [self.ctx.workflow, stats_wf]
        # (first run of create)
        # this call creates a list of workflows, starting w context workflow
        # then adds a stats_wf

        parent_workflow = hierarchy[-1] # = stats_wf (empty wf called stats_wf)

        variables = None
        if hasattr(model, "spreadsheet"):
            variables = self.ctx.database.metadata(model.spreadsheet, "variables")

        # inputs is a list of hierarchies (list of workflows)
        # ... list entries get named ouputhierarchy below
        input_hierarchies = []
        # TODO rename w inputhierarchies = []
        # TODO check what inputname actually is bc here it seems to refer to model inputs whereas in other calls it refers to models & features
        for inputname in model.inputs:
            # model.inputs must come from spec somehow, I can't find what they are other than a list of string
            logger.debug(f"StatsFactory->inputname: {inputname}")
            # Check if inputname is another model is present in spec (if inputname is another model should have been defined previously)
            if inputname in [model.name for model in self.ctx.spec.models]:
                # TODO problematic bc if true will call get on an empty dict for self.hierarchies
                # always bc model has to be in order, still feels messy
                input_hierarchies.extend(
                    self.get_hierarchy(inputname)
                    )

                logger.debug(f"StatsFactory->extending inputs by self->inputs: {inputs}")
            # Check if inputname is a feature
            elif inputname in [feature.name for feature in self.ctx.spec.features]:
                input_hierarchies.extend(
                    self.feature_factory.get(inputname)
                    )
                logger.debug(f"StatsFactory->extending inputs by feature_factory->inputs: {inputs}")
            else:
                raise ValueError(f'Unknown input name "{inputname}"')
        logger.debug(f"StatsFactory-> all gathered inputs: {inputs}")

        # create the actual wf
        workflow = init_stats_wf(
            self.ctx.workdir,
            model,
            numinputs=len(input_hierarchies),
            variables=variables,
        )
        # add the nodes of the created worfklow to the "stats_wf" (because its empty)
        parent_workflow.add_nodes([workflow]) # why is it a list of the workflow?
        # why add it again to the hierarchy?
        hierarchy.append(workflow)
        # hierarchy is now [self.ctx.workflow, stats_wf, workflow]
        # python question: is the stats_wf in this list filled w the nodes from line 76? if so workflow and stats_wf are the same?

        if model.name not in self.hierarchies:
            self.hierarchies[model.name] = []
        self.hierarchies[model.name].append(hierarchy)
        # at this self.hierarchies[model.name] is a list of of a list
        # [[self.ctx.workflow, stats_wf, workflow]]

        # renaming might be more confusing across Factories, but consistent internally at least
        for i, input_hierarchy in enumerate(input_hierarchies):
            self.connect_attr(
                input_hierarchy, # should be a hierarchy
                "outputnode",
                "resultdicts",
                hierarchy, # [self.ctx.workflow, stats_wf, workflow]
                "inputnode",
                f"in{i + 1:d}",
            )

        return workflow

    def get_hierarchy(self, model_name):
        """ Returns the hierarchy associated with the given model name. """
        return self.hierarchies[model_name]

    # TODO standardize
    def connect(self, *args, **kwargs):
        _, _ = args, kwargs
        raise NotImplementedError()
