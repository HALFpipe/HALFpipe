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
    def __init__(self, ctx, feature_factory: FeatureFactory) -> None:
        super().__init__(ctx)

        self.feature_factory = feature_factory

    def has(self, name: str) -> bool:
        for model in self.ctx.spec.models:
            if model.name == name:
                return True
        return False

    def setup(self):
        self.wfs = dict()
        for model in self.ctx.spec.models:
            self.create(model)

    def create(self, model):
        hierarchy = self._get_hierarchy("stats_wf")
        wf = hierarchy[-1]

        database = self.ctx.database

        variables = None
        if hasattr(model, "spreadsheet"):
            variables = database.metadata(model.spreadsheet, "variables")

        inputs = []
        for inputname in model.inputs:
            logger.info(f"StatsFactory->inputname: {inputname}")
            if self.has(inputname):
                inputs.extend(self.get(inputname))
                logger.info(f"StatsFactory->extending inputs by self->inputs: {inputs}")
            elif self.feature_factory.has(inputname):
                inputs.extend(self.feature_factory.get(inputname))
                logger.info(f"StatsFactory->extending inputs by feature_factory->inputs: {inputs}")
            else:
                raise ValueError(f'Unknown input name "{inputname}"')
        logger.info(f"StatsFactory->inputs: {inputs}")

        vwf = init_stats_wf(
            self.ctx.workdir,
            model,
            numinputs=len(inputs),
            variables=variables,
        )
        wf.add_nodes([vwf])
        hierarchy.append(vwf)

        if model.name not in self.wfs:
            self.wfs[model.name] = []
        self.wfs[model.name].append(hierarchy)

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

    def get(self, model_name):
        return self.wfs[model_name]

    def connect(self, *args, **kwargs):
        _, _ = args, kwargs
        raise NotImplementedError()
