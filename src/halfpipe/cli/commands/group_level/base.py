# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Mapping

from ....model.contrast import ModelContrastSchema
from ....model.filter import FilterSchema
from ....model.variable import VariableSchema

aliases: Mapping[str, str] = dict(reho="effect", falff="effect", alff="effect")

variable_schema = VariableSchema()
contrast_schema = ModelContrastSchema()
filter_schema = FilterSchema()
