# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from __future__ import annotations
from typing import Dict, Hashable, NamedTuple, Tuple, Sequence, Union, List
from typing_extensions import Literal

from collections import defaultdict, Counter
from math import isclose

import numpy as np

from nipype.interfaces.base import traits, DynamicTraitedSpec, BaseInterfaceInputSpec
from nipype.interfaces.io import add_traits, IOBase

from .base import ResultdictsOutputSpec
from ...model import entities, ResultdictSchema
from ...utils import ravel, logger

schema = ResultdictSchema()


class MeanStd(NamedTuple):
    type: Literal["mean_std"]
    mean: float
    std: float
    n: int
    missing: int

    @classmethod
    def build(cls, mean: float, std: float, n: int, missing: int) -> MeanStd:
        return cls(type="mean_std", mean=mean, std=std, n=n, missing=missing)

    @classmethod
    def from_array(cls, array: List[float]) -> MeanStd:
        value_array = np.array(array, dtype=float)
        return MeanStd.build(
            mean=float(np.nanmean(value_array)),
            std=float(np.nanstd(value_array)),
            missing=int(np.sum(np.isnan(value_array))),
            n=int(value_array.size),
        )

    @classmethod
    def aggregate(cls, values: Sequence[Union[Tuple, float, np.inexact]]) -> MeanStd:
        return cls.from_array([
            MeanStd(*v).mean if isinstance(v, tuple)
            else float(v)
            for v in values
        ])

    @classmethod
    def is_instance(cls, value) -> bool:
        if isinstance(value, MeanStd):
            return True
        elif isinstance(value, tuple) and len(value) == 5:
            type, mean, std, n, missing = value
            return (
                type == "mean_std"
                and isinstance(mean, float)
                and isinstance(std, float)
                and isinstance(n, int)
                and isinstance(missing, int)
            )
        else:
            return False


class BinCount(NamedTuple):
    value: Union[Hashable, Dict]
    count: int

    @classmethod
    def is_instance(cls, value) -> bool:
        if isinstance(value, BinCount):
            return True
        elif isinstance(value, tuple) and len(value) == 2:
            value, count = value
            return isinstance(count, int)
        else:
            return False


class BinCounts(NamedTuple):
    type: Literal["bin_counts"]
    counts: Tuple[BinCount, ...]

    @classmethod
    def build(cls, counter: Counter, value_was_dict: bool = False) -> BinCounts:
        counts = list()

        values = counter.keys()

        try:
            sorted_values = sorted(values)
        except TypeError:
            sorted_values = sorted(values, key=str)  # fallback lexical sort

        for v in sorted_values:
            count = counter[v]
            if value_was_dict is True:
                v = dict(v)
            counts.append(BinCount(value=v, count=count))

        return cls(type="bin_counts", counts=tuple(counts))

    @classmethod
    def aggregate(cls, values: Sequence[Tuple[BinCount, ...]], value_was_dict: bool = False) -> BinCounts:
        counter: Counter = Counter()
        for v in values:
            c, value_was_dict = cls.to_counter(v)
            counter.update(c)
        return cls.build(counter, value_was_dict=value_was_dict)

    @classmethod
    def to_counter(cls, counts: Tuple[BinCount, ...]) -> Tuple[Counter, bool]:
        value_was_dict = None

        counter: Counter = Counter()

        for count in counts:
            value = count.value

            if isinstance(value, dict):
                value_is_dict = True
                value = tuple(sorted(value.items()))
            else:
                value_is_dict = False

            assert value_was_dict == value_is_dict

            value_was_dict = value_is_dict

            counter.update({value: count.count})

        assert value_was_dict is not None
        return counter, value_was_dict

    @classmethod
    def is_instance(cls, value) -> bool:
        if isinstance(value, BinCounts):
            return True
        elif isinstance(value, tuple) and len(value) == 2:
            type, counts = value
            return (
                type == "bin_counts"
                and all(BinCount.is_instance(c) for c in counts)
            )
        else:
            return False


def aggregate_hashable(value: Sequence[Hashable], value_was_dict: bool):
    value_set = set(value)
    if len(value_set) == 1:
        result = next(iter(value_set))

        if value_was_dict:
            assert isinstance(result, Sequence)
            return dict(result)

        return result

    counter = Counter(value)
    return BinCounts.build(counter, value_was_dict=value_was_dict)


def aggregate_if_possible(value, value_was_dict: bool = False):
    if isinstance(value, (list, tuple)) and len(value) > 0:

        if all(isinstance(v, (float, np.inexact)) for v in value):
            if all(isclose(v, value[0]) for v in value):
                return value[0]
            else:
                return MeanStd.from_array(list(value))

        elif all(BinCounts.is_instance(v) for v in value):
            return BinCounts.aggregate(value, value_was_dict=value_was_dict)

        elif all(MeanStd.is_instance(v) or isinstance(v, (float, np.inexact)) for v in value):
            return MeanStd.aggregate(value)

        elif all(isinstance(v, Hashable) for v in value):  # str int and tuple
            return aggregate_hashable(value, value_was_dict)

        elif all(isinstance(val, list) for val in value):
            return aggregate_if_possible(tuple(map(tuple, value)))

        elif all(isinstance(val, dict) for val in value):
            return aggregate_if_possible(
                [tuple(sorted(v.items())) for v in value],
                value_was_dict=True,
            )

        raise ValueError(f'Cannot aggregate "{value}"')

    return value


def aggregate_list(value):
    result = list()
    for v in value:
        result.extend(v)
    return result


def aggregate_field(key, value):
    if key in ["sources", "raw_sources"]:
        return aggregate_list(value)

    return aggregate_if_possible(value)


def group_resultdicts(inputs, across):
    grouped_resultdicts = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for resultdict in sorted(inputs, key=lambda d: d["tags"][across]):
        tags = resultdict["tags"]

        if across not in tags:
            continue

        tag_tuple = tuple(sorted(
            (key, value)
            for key, value in tags.items()
            if key != across
            and not isinstance(value, (tuple, list))  # Ignore lists, as they only
            # will be there if we aggregated before, meaning that this is not
            # a tag that separates different results anymore.
            # This is important for example if we want have aggregated unequal numbers
            # of runs across subjects, but we still want to compare across subjects
        ))

        for f, nested in resultdict.items():
            for k, v in nested.items():
                grouped_resultdicts[tag_tuple][f][k].append(v)

    return grouped_resultdicts


def aggregate_resultdicts(inputs, across):
    grouped_resultdicts = group_resultdicts(inputs, across)

    aggregated = list()
    non_aggregated = list()

    for tag_tuple, listdict in grouped_resultdicts.items():
        resultdict = defaultdict(dict)
        resultdict["tags"] = dict(tag_tuple)

        for f, d in listdict.items():  # create combined resultdict
            resultdict[f].update(d)

        for f in ["tags", "metadata", "vals"]:
            for key, value in resultdict[f].items():
                if key == across:
                    assert all(isinstance(v, Hashable) for v in value)
                    resultdict[f][key] = list(value)
                    continue
                resultdict[f][key] = aggregate_field(key, value)

        validation_errors = schema.validate(resultdict)

        for f in ["tags", "metadata", "vals"]:
            if f in validation_errors:
                for key in validation_errors[f]:
                    logger.warning(f'Removing "{f}.{key}={resultdict[f][key]}" from resultdict')
                    del resultdict[f][key]  # remove invalid fields

        if any(
            isinstance(value, list) and len(value) > 1
            for value in resultdict["images"].values()
        ):
            aggregated.append(resultdict)
        else:
            non_aggregated.append(resultdict)

    return aggregated, non_aggregated


class AggregateResultdictsInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    across = traits.Enum(*entities, desc="across which entity to aggregate")


class AggregateResultdictsOutputSpec(ResultdictsOutputSpec):
    non_aggregated_resultdicts = traits.List(traits.Dict(traits.Str(), traits.Any()))


class AggregateResultdicts(IOBase):
    input_spec = AggregateResultdictsInputSpec
    output_spec = AggregateResultdictsOutputSpec

    def __init__(self, numinputs=0, **inputs):
        super(AggregateResultdicts, self).__init__(**inputs)
        self._numinputs = numinputs
        if numinputs >= 1:
            self.input_names = [f"in{i+1}" for i in range(numinputs)]
            add_traits(self.inputs, self.input_names)
        else:
            self.input_names = []

    def _list_outputs(self):
        outputs = self._outputs()
        assert outputs is not None
        outputs = outputs.get()

        inputs = ravel([getattr(self.inputs, input_name) for input_name in self.input_names])
        across = self.inputs.across

        aggregated, non_aggregated = aggregate_resultdicts(inputs, across)

        outputs["resultdicts"] = aggregated
        outputs["non_aggregated_resultdicts"] = non_aggregated

        return outputs
