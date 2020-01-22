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
    SimpleInterface
) 
from nipype.interfaces.io import (
    add_traits
)

import numpy as np


class HigherLevelDesignInputSpec(TraitedSpec):
    pass

class HigherLevelDesignOutputSpec(TraitedSpec):
    out = traits.Bool(desc="output")

class HigherLevelDesign(IOBase):
    """

    """

    input_spec = LogicalAndInputSpec
    output_spec = LogicalAndOutputSpec

    def __init__(self, numinputs=0, **inputs):
        super(Filter, self).__init__(**inputs)
        self._numinputs = numinputs
        if numinputs >= 1:
            input_names = ["in%d" % (i + 1) for i in range(numinputs)]
            add_traits(self.inputs, input_names, trait_type = traits.Bool)
        else:
            input_names = []

    def _list_outputs(self):
        outputs = self._outputs().get()
        out = []

        if self._numinputs < 1:
            return outputs

        getval = lambda idx: getattr(self.inputs, "in%d" % (idx + 1))
        values = [
            getval(idx) for idx in range(self._numinputs) 
                if isdefined(getval(idx))
        ]
        
        out = False
        
        if len(values) > 0:
            out = np.all(values)
        
        outputs["out"] = out
        
        return outputs