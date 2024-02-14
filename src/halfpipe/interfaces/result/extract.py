# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import BaseInterfaceInputSpec, DynamicTraitedSpec, traits
from nipype.interfaces.io import IOBase, add_traits

from ...model.resultdict import ResultdictSchema


class ExtractFromResultdictInputSpec(BaseInterfaceInputSpec):
    indict = traits.Dict(traits.Str(), traits.Any())


class ExtractFromResultdictOutputSpec(DynamicTraitedSpec):
    tags = traits.Dict(traits.Str(), traits.Any())
    metadata = traits.Dict(traits.Str(), traits.Any())
    vals = traits.Dict(traits.Str(), traits.Any())


class ExtractFromResultdict(IOBase):
    input_spec = ExtractFromResultdictInputSpec
    output_spec = ExtractFromResultdictOutputSpec

    def __init__(self, keys: list | None = None, aliases: dict | None = None, **inputs):
        super(ExtractFromResultdict, self).__init__(**inputs)

        self._keys = [] if keys is None else keys
        self._aliases = {} if aliases is None else aliases

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

            while key not in outdict and len(key_and_aliases) > 0:
                key_or_alias = key_and_aliases.pop()
                for v in resultdict.values():
                    if key_or_alias in v:
                        outdict[key] = v[key_or_alias]
                        del v[key_or_alias]
                        break

        for key in self._keys:
            if key in outdict:
                outputs[key] = outdict[key]
            else:
                outputs[key] = []

        outputs["tags"] = resultdict.get("tags")
        outputs["metadata"] = resultdict.get("metadata")
        outputs["vals"] = resultdict.get("vals")

        return outputs
