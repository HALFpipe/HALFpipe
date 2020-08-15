# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from nipype.pipeline.engine.utils import load_resultfile
from nipype.interfaces.base import TraitedSpec, DynamicTraitedSpec
from nipype.interfaces.io import IOBase, add_traits


class LoadResult(IOBase):
    """ load a result from cache """

    input_spec = TraitedSpec
    output_spec = DynamicTraitedSpec

    def __init__(self, node, **inputs):
        super(LoadResult, self).__init__(**inputs)
        self._resultfilepath = Path(node.output_dir()) / ("result_%s.pklz" % node.name)
        self._attrs = node.outputs.copyable_trait_names()

    def _add_output_traits(self, base):
        return add_traits(base, self._attrs)

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if not self._resultfilepath.is_file():
            return outputs

        result = load_resultfile(self._resultfilepath)
        try:
            cachedoutputs = result.outputs.get()
        except TypeError:  # This is a Bunch
            cachedoutputs = result.__dict__

        for attr in self._attrs:
            outputs[attr] = cachedoutputs[attr]

        return outputs
