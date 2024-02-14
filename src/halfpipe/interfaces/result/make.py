# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from collections import defaultdict
from typing import Any

from nipype.interfaces.base import DynamicTraitedSpec, isdefined, traits
from nipype.interfaces.io import IOBase, add_traits

from ...model.resultdict import ResultdictSchema
from ...model.utils import get_schema_entities
from ...result.base import ResultDict
from ...utils.copy import deepcopy
from ...utils.ops import ravel
from .base import ResultdictsOutputSpec

resultdict_schema = ResultdictSchema()
resultdict_entities = set(get_schema_entities(resultdict_schema))

composite_attr = re.compile(r"(?P<tag>[a-z]+)_(?P<attr>[a-z]+)")


class MakeResultdictsOutputSpec(ResultdictsOutputSpec):
    vals = traits.Dict(traits.Str(), traits.Any())


class MakeResultdicts(IOBase):
    input_spec = DynamicTraitedSpec
    output_spec = MakeResultdictsOutputSpec

    def __init__(
        self,
        dictkeys: list[str] | None = None,
        tagkeys: list[str] | None = None,
        valkeys: list[str] | None = None,
        imagekeys: list[str] | None = None,
        reportkeys: list[str] | None = None,
        metadatakeys: list[str] | None = None,
        nobroadcastkeys: list[str] | None = None,
        deletekeys: list[str] | None = None,
        missingvalues: list[Any] | None = None,
        **inputs,
    ):
        super(MakeResultdicts, self).__init__(**inputs)

        if dictkeys is None:
            dictkeys = ["tags", "metadata", "vals"]
        if tagkeys is None:
            tagkeys = list()
        if valkeys is None:
            valkeys = list()
        if imagekeys is None:
            imagekeys = list()
        if reportkeys is None:
            reportkeys = list()
        if metadatakeys is None:
            metadatakeys = list()
        if nobroadcastkeys is None:
            nobroadcastkeys = list()
        if deletekeys is None:
            deletekeys = list()
        if missingvalues is None:
            missingvalues = [None]

        add_traits(
            self.inputs,
            [*tagkeys, *valkeys, *imagekeys, *reportkeys, *metadatakeys, *dictkeys],
        )
        self._dictkeys = dictkeys
        self._keys = {
            "tags": tagkeys,
            "vals": valkeys,
            "images": imagekeys,
            "reports": reportkeys,
            "metadata": metadatakeys,
        }
        self._nobroadcastkeys = nobroadcastkeys
        self._deletekeys = deletekeys
        self._missingvalues = missingvalues

    def _list_outputs(self):
        output_spec = self._outputs()
        assert output_spec is not None
        outputs = output_spec.get()

        inputs: list[tuple[str, str | None, Any]] = [
            (fieldname, None, getattr(self.inputs, fieldname))
            for fieldname in self._dictkeys
            if isdefined(getattr(self.inputs, fieldname))
        ]
        inputs.extend(
            [
                (fieldname, key, getattr(self.inputs, key))
                for fieldname, keys in self._keys.items()
                for key in keys
                if isdefined(getattr(self.inputs, key))
            ]
        )
        if len(inputs) == 0:
            outputs["resultdicts"] = []
            return outputs

        fieldnames, keys, values = map(list, zip(*inputs, strict=False))

        # remove undefined
        undefined_indices = set()
        for i in range(len(values)):
            value = values[i]
            if isinstance(value, list):
                for j, v in enumerate(value):
                    if not isdefined(v):
                        undefined_indices.add(j)
        for i in range(len(values)):
            value = values[i]
            if isinstance(value, list):
                for j in sorted(undefined_indices, reverse=True):
                    del value[j]

        # determine broadcasting rule
        maxlen = 1
        nbroadcast = None
        for i in range(len(values)):
            if keys[i] in self._nobroadcastkeys:
                continue

            value = values[i]
            if isinstance(value, (list, tuple)):
                if all(isinstance(elem, (list, tuple)) for elem in value):
                    size = len(ravel(value))
                    lens = tuple(len(elem) for elem in value)
                    if nbroadcast is None:
                        nbroadcast = lens
                    else:
                        nbroadcast = tuple(max(a, b) for a, b in zip(lens, nbroadcast, strict=False))
                else:
                    size = len(value)
                if size > maxlen:
                    maxlen = size

        # broadcast values if necessary
        for i in range(len(values)):
            if isinstance(values[i], tuple):
                values[i] = list(values[i])
            if not isinstance(values[i], list):
                values[i] = [values[i]]
            if len(values[i]) == 1:  # broadcasting
                values[i] *= maxlen
            if len(values[i]) == 0:
                values[i] = [None] * maxlen
            if len(values[i]) != maxlen and len(ravel(values[i])) != maxlen:
                if nbroadcast is not None and len(values[i]) < maxlen and len(values[i]) == len(nbroadcast):
                    values[i] = ravel([[v] * m for m, v in zip(nbroadcast, values[i], strict=False)])
                else:
                    raise ValueError(f"Can't broadcast lists of lengths {len(values[i]):d} and {maxlen:d}")

        # flatten
        for i in range(len(values)):
            if keys[i] in self._nobroadcastkeys:
                continue

            values[i] = ravel(values[i])

        # make resultdicts
        resultdicts = []
        for valuetupl in zip(*values, strict=False):
            resultdict: ResultDict = defaultdict(dict)
            for f, k, v in zip(fieldnames, keys, valuetupl, strict=False):
                if k is None:
                    resultdict[f].update(v)
            # filter tags
            resultdict["tags"] = {k: v for k, v in resultdict["tags"].items() if k in resultdict_entities}
            for f, k, v in zip(fieldnames, keys, valuetupl, strict=False):
                # actually add values
                if k is not None and v not in self._missingvalues:
                    resultdict[f][k] = v
            resultdicts.append(resultdict)

        # apply composite attr rule
        for i in range(len(resultdicts)):
            newimages = dict()
            for k, v in resultdicts[i]["images"].items():
                m = composite_attr.fullmatch(k)
                if m is not None:  # apply rule
                    newresultsdict = deepcopy(resultdicts[i])
                    k = m.group("attr")
                    if k in ["ortho"]:
                        newresultsdict["tags"]["stat"] = m.group("tag")
                    else:
                        newresultsdict["tags"]["desc"] = m.group("tag")
                    newresultsdict["images"] = {k: v}
                    resultdicts.append(newresultsdict)
                else:
                    newimages[k] = v
            resultdicts[i]["images"] = newimages

        # delete keys
        for f, keys in self._keys.items():
            for k in keys:
                if k in self._deletekeys:
                    for i in range(len(resultdicts)):
                        if k in resultdicts[i][f]:
                            del resultdicts[i][f][k]

        # validate
        for i in range(len(resultdicts)):
            assert len(resultdict_schema.validate(resultdicts[i])) == 0  # type: ignore

        outputs["resultdicts"] = resultdicts
        outputs["vals"] = resultdicts[0]["vals"]

        return outputs
