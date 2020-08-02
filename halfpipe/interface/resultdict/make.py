# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import (
    traits,
    DynamicTraitedSpec,
    BaseInterfaceInputSpec,
)
from nipype.interfaces.io import add_traits, IOBase

from .base import ResultdictsOutputSpec
from ...model import ResultdictSchema


class MakeResultdictsInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    tags = traits.Dict(traits.Str(), traits.Any())
    metadata = traits.Dict(traits.Str(), traits.Any())


class MakeResultdicts(IOBase):
    input_spec = MakeResultdictsInputSpec
    output_spec = ResultdictsOutputSpec

    def __init__(self, valkeys=[], imagekeys=[], reportkeys=[], **inputs):
        super(MakeResultdicts, self).__init__(**inputs)
        add_traits(self.inputs, [*valkeys, *imagekeys, *reportkeys])
        self._keys = {"vals": valkeys, "images": imagekeys, "reports": reportkeys}

    def _list_outputs(self):
        outputs = self._outputs().get()

        inputs = [
            (fieldname, key, getattr(self.inputs, key))
            for fieldname, keys in self._keys.items()
            for key in keys
        ]
        if len(inputs) == 0:
            outputs["resultdicts"] = []
            return outputs

        fieldnames, keys, values = zip(*inputs)

        maxlen = max(len(value) if isinstance(value, (list, tuple)) else 1 for value in values)
        for i in range(len(values)):
            if isinstance(values[i], tuple):
                values[i] = list(values[i])
            if not isinstance(values[i], list):
                values[i] = [values[i]]
            if len(values[i]) == 1:  # simple broadcasting
                values[i] *= maxlen
            if len(values[i]) == 0:
                values[i] = [None] * maxlen
            assert len(values[i]) == maxlen, "Can't broadcast lists"

        valuetupls = zip(*values)

        resultdicts = []
        for valuetupl in valuetupls:
            resultdict = {
                "tags": dict(**self.inputs.tags),
                "metadata": dict(**self.inputs.metadata),
            }
            for f, k, v in zip(fieldnames, keys, valuetupl):
                if f not in resultdict:
                    resultdict[f] = dict()
                if v is not None:
                    resultdict[f][k] = v
            resultdicts.append(ResultdictSchema().load(resultdict))

        outputs["resultdicts"] = resultdicts

        return outputs
