# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

from nipype.pipeline.engine.utils import load_resultfile
from nipype.interfaces.base import (
    TraitedSpec,
    SimpleInterface,
    DynamicTraitedSpec,
)
from nipype.interfaces.io import add_traits


class LoadResult(SimpleInterface):
    """ interface to construct a group design """

    input_spec = TraitedSpec
    output_spec = DynamicTraitedSpec

    def __init__(self, node, attrs, **inputs):
        super(LoadResult, self).__init__(**inputs)
        cwd = node.output_dir()
        self._resultfilepath = op.join(cwd, "result_%s.pklz" % node.name)
        self._attrs = attrs

    def _add_output_traits(self, base):
        return add_traits(base, self._attrs)

    def _run_interface(self, runtime):
        outputs = self.output_spec().get()

        assert op.isfile(self._resultfilepath)

        result = load_resultfile(self._resultfilepath)
        try:
            cachedoutputs = result.outputs.get()
        except TypeError:  # This is a Bunch
            cachedoutputs = result.__dict__

        for attr in self._attrs:
            outputs[attr] = cachedoutputs[attr]

        return runtime
