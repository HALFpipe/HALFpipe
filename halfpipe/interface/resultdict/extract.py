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
    tags = traits.Dict(traits.Str(), traits.Any())
    metadata = traits.Dict(traits.Str(), traits.Any())
    vals = traits.Dict(traits.Str(), traits.Any())


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
        assert isinstance(resultdict, dict)

        outdict = dict()

        for key in self._keys:
            key_and_aliases = [key]
            if key in self._aliases:
                key_and_aliases.extend(self._aliases[key])
            for key_or_alias in key_and_aliases:
                for v in resultdict.values():
                    if key_or_alias in v:
                        outdict[key] = v[key_or_alias]
                        del v[key_or_alias]
                        return

        for key in self._keys:
            if key in outdict:
                outputs[key] = outdict[key]
            else:
                outputs[key] = []

        outputs["tags"] = resultdict.get("tags")
        outputs["metadata"] = resultdict.get("metadata")
        outputs["vals"] = resultdict.get("vals")

        return outputs
