# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Any, Hashable, NamedTuple, Tuple

from collections import defaultdict, Counter
from math import sqrt, isclose

import numpy as np

from nipype.interfaces.base import traits, DynamicTraitedSpec, BaseInterfaceInputSpec
from nipype.interfaces.io import add_traits, IOBase

from .base import ResultdictsOutputSpec
from ...model import entities, ResultdictSchema
from ...utils import ravel, logger


class MeanStd(NamedTuple):
    mean: float
    std: float
    n: int
    missing: int


class BinCount(NamedTuple):
    value: Any
    count: int


def bin_counts_to_counter(bin_counts: Tuple[BinCount, ...]) -> Tuple[Counter, bool]:
    value_was_dict = None

    counter: Counter = Counter()

    for bin_count in bin_counts:
        value = bin_count.value
        value_is_dict = isinstance(value, dict)

        if value_is_dict:
            assert value_was_dict is not False
            value = tuple(sorted(value.items()))
        else:
            assert value_was_dict is not True

        value_was_dict = value_is_dict

        counter.update({value: bin_count.count})

    assert value_was_dict is not None
    return counter, value_was_dict


def counter_to_bin_counts(counter: Counter, value_was_dict=False) -> Tuple[BinCount, ...]:
    bin_counts = list()
    for v in sorted(counter.keys()):
        count = counter[v]
        if value_was_dict is True:
            v = dict(v)
        bin_counts.append(BinCount(value=v, count=count))
    return tuple(bin_counts)


def aggregate_if_possible(value, value_was_dict=False):
    if isinstance(value, (list, tuple)) and len(value) > 0:

        if all(isinstance(v, (float, np.inexact)) for v in value):
            if all(isclose(v, value[0]) for v in value):
                return value[0]

            value_array = np.array(value, dtype=float)
            return MeanStd(
                mean=float(np.nanmean(value_array)),
                std=float(np.nanstd(value_array)),
                missing=int(np.sum(np.isnan(value_array))),
                n=int(value_array.size),
            )

        elif all(
            isinstance(v, tuple)
            and len(v) > 0
            and all(isinstance(w, BinCount) for w in v)
            for v in value
        ):
            counter: Counter = Counter()
            for v in value:
                c, value_was_dict = bin_counts_to_counter(v)
                counter.update(c)
            return counter_to_bin_counts(counter, value_was_dict=value_was_dict)

        elif all(isinstance(v, MeanStd) for v in value):
            n = sum(v.n for v in value)

            pooled_std = sqrt(sum(v.std * v.std * (v.n - 1) for v in value) / (n - len(value)))

            return MeanStd(
                mean=sum(v.mean * v.n for v in value) / n,
                std=pooled_std,
                n=int(n),
                missing=sum(v.missing for v in value),
            )

        elif all(isinstance(v, Hashable) for v in value):  # str int and tuple
            value_set = set(value)
            if len(value_set) == 1:
                result = next(iter(value_set))

                if value_was_dict:
                    return dict(result)

                return result

            counter = Counter(value)
            return counter_to_bin_counts(counter, value_was_dict=value_was_dict)

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
                    resultdict[f][key] = tuple(value)
                    continue
                resultdict[f][key] = aggregate_field(key, value)

        schema = ResultdictSchema()
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
