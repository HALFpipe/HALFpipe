# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import marshmallow
from marshmallow import (
    Schema,
    fields
)
from marshmallow_oneofschema import OneOfSchema


class SubjectLevelAnalysisSpec:
    def __init__(self, name, tags):
        self.name = name
        self.tags = tags


class SubjectLevelAnalysisSpecSchema(Schema):
    name = fields.Str()
    tags = fields.Str()


class TaskBasedGLMAnalysisSpec(SubjectLevelAnalysisSpec):
    def __init__(self, name, tags, files, contrasts):
        super(TaskBasedGLMAnalysisSpec, self).__init__(
            name, tags
        )
        self.files = files
        self.contrasts = contrasts


class TaskBasedGLMAnalysisSpecSchema(Schema):
    pass


class SeedBasedConnectivityAnalysisSpec(SubjectLevelAnalysisSpec):
    def __init__(self, name, tags, files):
        super(SeedBasedConnectivityAnalysisSpec, self).__init__(
            name, tags
        )
        self.files = files


class DualRegressionAnalysisSpec(SubjectLevelAnalysisSpec):
    def __init__(self, name, tags, files):
        super(DualRegressionAnalysisSpec, self).__init__(
            name, tags
        )
        self.files = files


class AtlasBasedConnectivityAnalysisSpec(SubjectLevelAnalysisSpec):
    def __init__(self, name, tags, files):
        super(AtlasBasedConnectivityAnalysisSpec, self).__init__(
            name, tags
        )
        self.files = files


class FALFFAnalysisSpec(SubjectLevelAnalysisSpec):
    def __init__(self, name, tags, files):
        super(FALFFAnalysisSpec, self).__init__(
            name, tags
        )


class ReHoAnalysisSpec(SubjectLevelAnalysisSpec):
    def __init__(self, name, tags, files):
        super(ReHoAnalysisSpec, self).__init__(
            name, tags
        )