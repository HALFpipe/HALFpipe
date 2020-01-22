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

def _qualitycheck(base_directory = None, subject = None, task = None):
    
    qcresult_fname = os.path.join(base_directory, "qualitycheck", "qcresult.json")
    
    qcresult = dictionary()
    if os.path.isfile(qcresult_fname):
        with open(qcresult_fname) as qcresult_file:
            qcresult = json.load(qcresult_file)
    
    is_good = True
    for s, value0 in qcresult.items():
        if s == subject:
            for t, value1 in value0.items():
                for run, value2 in value1.items():
                    if t == "T1w" or t == task:
                        for k, v in value2.items():
                            if v == "bad":
                                is_good = False
                        
    
    return is_good

class QualityCheckInputSpec(TraitedSpec):
    pass

class QualityCheckOutputSpec(TraitedSpec):
    keep = traits.Bool(desc="Decision, true means keep")

class QualityCheck(SimpleInterface):
    """

    """

    input_spec = QualityCheckInputSpec
    output_spec = QualityCheckOutputSpec

    def __init__(self, 
        base_directory = None, subject = None, task = None, **inputs):
        super(QualityCheck, self).__init__(**inputs) 
        
        self.base_directory = base_directory
        self.subject = subject
        self.task = task

    def _run_interface(self, runtime):
        keep = _qualitycheck(
            base_directory = self.base_directory,
            subject = self.subject,
            task = self.task,
        )
        self._results["keep"] = keep
        
        return runtime


