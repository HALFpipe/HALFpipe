# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import (
    traits,
    DynamicTraitedSpec,
    BaseInterfaceInputSpec,
)
from nipype.interfaces.io import add_traits, IOBase

from ...model import ResultdictSchema


class ExtractFromResultdictInputSpec(BaseInterfaceInputSpec):
    indict = traits.Dict(traits.Str(), traits.Any())


class ExtractFromResultdictOutputSpec(DynamicTraitedSpec):
    remainder = traits.Dict(traits.Str(), traits.Any())


class ExtractFromResultdict(IOBase):
    input_spec = ExtractFromResultdictInputSpec
    output_spec = ExtractFromResultdictOutputSpec

    def __init__(self, keys=[], aliases={}, **inputs):
        super(ExtractFromResultdict, self).__init__(**inputs)
        self._keys = keys
        self._aliases = aliases

    def _add_output_traits(self, base):
        return add_traits(base, self._keys)

    def _list_outputs(self):
        outputs = self.output_spec().get()

        resultdict_schema = ResultdictSchema()
        resultdict = resultdict_schema.load(self.inputs.indict)

        images = resultdict.get("images")

        outdict = dict()
        for key in self._keys:
            keys = [key]
            if key in self._aliases:
                keys.extend(self._aliases[key])
            for inkey in keys:
                if inkey in images:
                    outdict[key] = images[inkey]
                    del images[inkey]
                    break

        for key in self._keys:
            if key in outdict:
                outputs[key] = outdict[key]
            else:
                outputs[key] = []

        outputs["remainder"] = resultdict_schema.dump(resultdict)

        return outputs
