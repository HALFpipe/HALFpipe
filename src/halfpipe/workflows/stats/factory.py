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
        self.wfs = dict()

    # TODO standardize
    def connect(self, *args, **kwargs):
        _, _ = args, kwargs
        raise NotImplementedError()

    def get(self, model_name):
        # TODO add check if model_name in wfs
        return self.wfs[model_name]

    # TODO rename to _create
    def create(self, model):
        hierarchy = self._get_hierarchy("stats_wf")
        # (first run of create)
        # this call creates a list of workflows, starting w context workflow
        # then adds a stats_wf

        # this is just an empty wf called stats_wf
        wf = hierarchy[-1]

        variables = None
        if hasattr(model, "spreadsheet"):
            variables = self.ctx.database.metadata(model.spreadsheet, "variables")

        # inputs is a list of hierarchies (list of workflows)
        # ... list entries get named ouputhierarchy below
        inputs = []
        # TODO check what inputname actually is bc here it seems to refer to model inputs whereas in other calls it refers to models & features
        for inputname in model.inputs:
            logger.debug(f"StatsFactory->inputname: {inputname}")
            # Check if model is present in spec
            # TODO naming is confusing but this is correct according to code replaced
            # if self.has(inputname):

            # if inputname is another model should have been defined previously
            if inputname in [model.name for model in self.ctx.spec.models]:
                # TODO problematic bc if true will call get on an empty dict for self.wfs
                # will this always be false?
                inputs.extend(self.get(inputname))
                logger.debug(f"StatsFactory->extending inputs by self->inputs: {inputs}")

                # case never happens bc model has to be in order

            # elif self.feature_factory.has(inputname):
            elif inputname in [feature.name for feature in self.ctx.spec.features]:
                inputs.extend(self.feature_factory.get(inputname))
                logger.debug(f"StatsFactory->extending inputs by feature_factory->inputs: {inputs}")
            else:
                raise ValueError(f'Unknown input name "{inputname}"')
        logger.debug(f"StatsFactory-> all gathered inputs: {inputs}")

        # create the actual wf
        vwf = init_stats_wf(
            self.ctx.workdir,
            model,
            numinputs=len(inputs),
            variables=variables,
        )
        # Why do we add the nodes of the worfklow to the current last element of hierarchy "stats_wf"
        # python pointers question is this modification of the wf gonna be included in the old list
        wf.add_nodes([vwf])
        # and then add it again to the hierarchy?
        hierarchy.append(vwf)

        # here its named a hierarchy
        if model.name not in self.wfs:
            # self.wfs[model.name] = []
            self.wfs[model.name] = [hierarchy]
            # dont like that this a list of hierarchy where its just hierarchy in other feature factory
        # self.wfs[model.name].append(hierarchy)
        # at this self.wfs[model.name] is a list of of a list
        # [[outer_workflow, stats_wf, vwf]]

        # inputs is a list of outputhierarchy??
        for i, outputhierarchy in enumerate(inputs):
            self.connect_attr(
                outputhierarchy,
                "outputnode",
                "resultdicts",
                hierarchy,
                "inputnode",
                f"in{i + 1:d}",
            )

        return vwf

    # TODO standardize
    # this should be the only callable function from any factory?
    def setup(self):
        for model in self.ctx.spec.models:
            self.create(model)
