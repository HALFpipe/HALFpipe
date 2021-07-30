# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re

from .base import init_model_wf

from ..factory import Factory


inputnode_name = re.compile(r"(?P<prefix>[a-z]+_)?inputnode")


class ModelFactory(Factory):
    def __init__(self, ctx, feature_factory):
        super(ModelFactory, self).__init__(ctx)

        self.feature_factory = feature_factory

    def has(self, name):
        for model in self.spec.models:
            if model.name == name:
                return True
        return False

    def setup(self):
        self.wfs = dict()
        for model in self.spec.models:
            self.create(model)

    def create(self, model):
        hierarchy = self._get_hierarchy("models_wf")
        wf = hierarchy[-1]

        database = self.database

        variables = None
        if hasattr(model, "spreadsheet"):
            variables = database.metadata(model.spreadsheet, "variables")

        inputs = []
        for inputname in model.inputs:
            if self.has(inputname):
                inputs.extend(self.get(inputname))
            elif self.feature_factory.has(inputname):
                inputs.extend(self.feature_factory.get(inputname))
            else:
                raise ValueError(f'Unknown input name "{inputname}"')

        vwf = init_model_wf(
            numinputs=len(inputs),
            model=model,
            variables=variables,
            workdir=str(self.workdir),
        )
        wf.add_nodes([vwf])
        hierarchy.append(vwf)

        if model.name not in self.wfs:
            self.wfs[model.name] = []
        self.wfs[model.name].append(hierarchy)

        for i, outputhierarchy in enumerate(inputs):
            self.connect_attr(outputhierarchy, "outputnode", "resultdicts", hierarchy, "inputnode", f"in{i+1:d}")

        return vwf

    def get(self, model_name):
        return self.wfs[model_name]

    def connect(self, *args, **kwargs):
        raise NotImplementedError()
