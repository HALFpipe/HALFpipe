# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

import os

from nipype.interfaces.base import (
    DynamicTraitedSpec,
    File,
    InputMultiPath,
    isdefined,
    traits,
)
from nipype.interfaces.io import IOBase, add_traits

from ...stats.algorithms import algorithms, make_algorithms_set
from ...stats.fit import fit
from .design import DesignSpec


class ModelFitInputSpec(DesignSpec):
    cope_files = InputMultiPath(
        File(exists=True),
        mandatory=True,
    )
    var_cope_files = InputMultiPath(
        File(exists=True),
        mandatory=False,
    )
    mask_files = InputMultiPath(
        File(exists=True),
        mandatory=True,
    )

    algorithms_to_run = traits.List(
        traits.Enum(*algorithms.keys()),
        value=["flame1"],
        usedefault=True,
    )

    num_threads = traits.Int(1, usedefault=True)


class ModelFit(IOBase):
    input_spec = ModelFitInputSpec
    output_spec = DynamicTraitedSpec

    def __init__(self, **inputs):
        super(ModelFit, self).__init__(**inputs)
        self._results = dict()

    def _add_output_traits(self, base):
        algorithm_set = make_algorithms_set(self.inputs.algorithms_to_run)
        fieldnames = list()
        for a in algorithm_set:
            algorithm = algorithms[a]
            fieldnames.extend(algorithm.model_outputs)
            fieldnames.extend(algorithm.contrast_outputs)
        return add_traits(base, fieldnames)

    def _list_outputs(self):
        return self._results

    def _run_interface(self, runtime):
        var_cope_files = self.inputs.var_cope_files

        if not isdefined(var_cope_files):
            var_cope_files = None

        prev_os_environ = os.environ.copy()
        os.environ.update(
            {
                "MKL_NUM_THREADS": "1",
                "NUMEXPR_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
            }
        )

        self._results.update(
            fit(
                cope_files=self.inputs.cope_files,
                var_cope_files=var_cope_files,
                mask_files=self.inputs.mask_files,
                regressors=self.inputs.regressors,
                contrasts=self.inputs.contrasts,
                algorithms_to_run=self.inputs.algorithms_to_run,
                num_threads=self.inputs.num_threads,
            )
        )

        os.environ.update(prev_os_environ)

        return runtime
