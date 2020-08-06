# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re

from nipype.interfaces.base import (
    traits,
    isdefined,
    DynamicTraitedSpec,
    BaseInterfaceInputSpec,
)
from nipype.interfaces.io import add_traits, IOBase

from .base import ResultdictsOutputSpec
from ...model import ResultdictSchema
from ...utils import ravel, lenforeach

composite_attr = re.compile(r"(?P<tag>[a-z]+)_(?P<attr>[a-z]+)")


class MakeResultdictsInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    tags = traits.Dict(traits.Str(), traits.Any())
    metadata = traits.Dict(traits.Str(), traits.Any())


class MakeResultdicts(IOBase):
    input_spec = MakeResultdictsInputSpec
    output_spec = ResultdictsOutputSpec

    def __init__(
        self, tagkeys=[], valkeys=[], imagekeys=[], reportkeys=[], metadatakeys=[], **inputs
    ):
        super(MakeResultdicts, self).__init__(**inputs)
        add_traits(self.inputs, [*tagkeys, *valkeys, *imagekeys, *reportkeys, *metadatakeys])
        self._keys = {
            "tags": tagkeys,
            "vals": valkeys,
            "images": imagekeys,
            "reports": reportkeys,
            "metadata": metadatakeys,
        }

    def _list_outputs(self):
        outputs = self._outputs().get()

        inputs = [
            (fieldname, key, getattr(self.inputs, key))
            for fieldname, keys in self._keys.items()
            for key in keys
            if isdefined(getattr(self.inputs, key))
        ]
        if len(inputs) == 0:
            outputs["resultdicts"] = []
            return outputs

        fieldnames, keys, values = map(list, zip(*inputs))

        maxlen = 1
        nbroadcast = None
        for value in values:
            if isinstance(value, (list, tuple)):
                size = len(ravel(value))
                if size > maxlen:
                    maxlen = size
                if nbroadcast is None:
                    nbroadcast = tuple(lenforeach(value))
                else:
                    assert tuple(lenforeach(value)) == nbroadcast

        for i in range(len(values)):
            if isinstance(values[i], tuple):
                values[i] = list(values[i])
            if not isinstance(values[i], list):
                values[i] = [values[i]]
            if len(values[i]) == 1:  # simple broadcasting
                values[i] *= maxlen
            if len(values[i]) == 0:
                values[i] = [None] * maxlen
            if len(values[i]) != maxlen:
                if len(values[i]) < maxlen and len(values[i]) == len(nbroadcast):
                    values[i] = ravel([[v] * m for m, v in zip(nbroadcast, values[i])])
                else:
                    raise ValueError(
                        f"Can't broadcast lists of lengths {len(values[i]):d} and {maxlen:d}"
                    )

        valuetupls = zip(*values)

        resultdicts = []
        for valuetupl in valuetupls:
            resultdict = dict(tags=dict(), metadata=dict())
            if isdefined(self.inputs.tags) and isinstance(self.inputs.tags, dict):
                resultdict["tags"] = dict(**self.inputs.tags)
            if isdefined(self.inputs.metadata) and isinstance(self.inputs.metadata, dict):
                resultdict["metadata"] = dict(**self.inputs.metadata)
            for f, k, v in zip(fieldnames, keys, valuetupl):
                if f == "images":
                    m = composite_attr.fullmatch(k)
                    if m is not None:  # apply rule
                        k = m.group("attr")
                        if k in ["ortho"]:
                            resultdict["tags"]["stat"] = m.group("tag")
                        else:
                            resultdict["tags"]["desc"] = m.group("tag")
                # actually add
                if f not in resultdict:
                    resultdict[f] = dict()
                if v is not None:
                    resultdict[f][k] = v
            resultdicts.append(ResultdictSchema().load(resultdict))

        outputs["resultdicts"] = resultdicts

        return outputs
