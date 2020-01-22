# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import json
import pandas as pd

from nipype.interfaces.base import ( 
    isdefined,
    traits,
    TraitedSpec, 
    DynamicTraitedSpec,
    SimpleInterface,
    BaseInterface
) 
from nipype.interfaces.io import (
    add_traits
)

import numpy as np


class HigherLevelDesignInputSpec(TraitedSpec):
    pass

class HigherLevelDesignOutputSpec(TraitedSpec):
    out = traits.Bool(desc="output")

class HigherLevelDesign(BaseInterface):
    """

    """

    input_spec = HigherLevelDesignInputSpec
    output_spec = HigherLevelDesignOutputSpec

    def _run_interface(self, runtime):
        pass