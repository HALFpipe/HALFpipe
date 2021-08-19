# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from __future__ import annotations
from typing import Any, Dict, Hashable, Iterable, Mapping, Optional, Tuple, Sequence, Union, List

from dataclasses import fields
from collections import defaultdict, Counter
from math import isclose

import numpy as np
from frozendict import frozendict

from nipype.interfaces.base import traits, DynamicTraitedSpec, BaseInterfaceInputSpec
from nipype.interfaces.io import add_traits, IOBase

from .base import ResultdictsOutputSpec
from ...utils import ravel, logger
from ...schema.result import MeanStd, Count, Result

schema = Result.Schema()


def aggregate_continuous(
    values: Sequence[Union[MeanStd, float, np.inexact]]
) -> Optional[Union[float, dict]]:
    scalar_values: List[float] = list()
    mean_std_values: List[MeanStd] = list()

    for value in values:
        if isinstance(value, float):
            scalar_values.append(value)
        elif isinstance(value, np.inexact):
            scalar_values.append(float(value))
        elif isinstance(value, MeanStd):
            scalar_values.append(value.mean)
            mean_std_values.append(value)
        else:
            return None

    if all(isclose(v, scalar_values[0]) for v in scalar_values):
        return scalar_values[0]

    mean_std = MeanStd.from_array([
        value.mean if isinstance(value, MeanStd)
        else float(value)
        for value in values
    ])
    mean_std_dict = MeanStd.Schema().dump(mean_std)
    assert isinstance(mean_std_dict, dict)

    return mean_std_dict


def count_list_from_counter(counter: Counter, value_was_dict: bool = False) -> List[Count]:
    count_list: List[Count] = list()

    values = counter.keys()

    try:
        sorted_values = sorted(values)
    except TypeError:
        sorted_values = sorted(values, key=str)  # fallback lexical sort

    for v in sorted_values:
        count = counter[v]
        if value_was_dict is True:
            v = dict(v)
        count_list.append(Count(value=v, count=count))

    return count_list


def counter_from_count_list(count_list: Sequence[Count]) -> Tuple[Counter, bool]:
    value_was_dict = None

    counter: Counter = Counter()

    for count in count_list:
        value = count.value

        if isinstance(value, dict):
            value_is_dict = True
            value = tuple(sorted(value.items()))
        else:
            value_is_dict = False

        assert value_was_dict is None or value_is_dict is None or value_was_dict == value_is_dict

        value_was_dict = value_is_dict

        counter.update({value: count.count})

    assert value_was_dict is not None

    return counter, value_was_dict


def aggregate_categorical(values: Sequence, value_was_dict: bool):
    counter: Counter = Counter()

    for value in values:
        if isinstance(value, Sequence):
            if all(isinstance(count, Count) for count in value):
                value_counter, value_was_dict = counter_from_count_list(value)
                counter.update(value_counter)
                continue

        counter.update({value: 1})

    count_list = count_list_from_counter(counter, value_was_dict=value_was_dict)

    if len(count_list) == 1:
        (count,) = count_list
        return count.value

    count_dict_list = Count.Schema().dump(count_list, many=True)
    assert isinstance(count_dict_list, list)

    return count_dict_list


def freeze_any(x: Any) -> Hashable:
    try:
        _ = hash(x)
        return x
    except TypeError as e:  # is not hashable
        if isinstance(x, Sequence):
            sequence: List[Hashable] = [
                freeze_any(element) for element in x
            ]
            return tuple(sequence)
        elif isinstance(x, Mapping):
            mapping: List[Tuple[Hashable, Hashable]] = [
                (freeze_any(k), freeze_any(v), )
                for k, v in x.items()
            ]
            return frozendict(mapping)
        elif isinstance(x, Iterable):
            iterable: List[Hashable] = [
                freeze_any(element) for element in x
            ]
            return frozenset(iterable)
        elif isinstance(x, (MeanStd, Count)):  # special dataclasses
            return x
        elif hasattr(x, "Schema"):  # other dataclasses
            return freeze_any(x.Schema().dump(x))

        raise ValueError(f'Cannot freeze {x}') from e


def aggregate_any(values: Any, value_was_dict: bool = False):
    values = freeze_any(values)

    if not isinstance(values, (list, tuple)) or len(values) == 0:
        return values

    result = aggregate_continuous(values)
    if result is None:
        result = aggregate_categorical(values, value_was_dict=value_was_dict)

    if result is not None:
        return result

    raise ValueError(f'Cannot aggregate "{values}"')


def aggregate_list(value):
    result = list()
    for v in value:
        result.extend(v)
    return result


def aggregate_field(key, value):
    if key in ["sources", "raw_sources"]:
        return aggregate_list(value)

    return aggregate_any(value)


def group_resultdicts(inputs, across):
    grouped_resultdicts = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for resultdict in sorted(inputs, key=lambda d: d["tags"][across]):
        result = schema.load(data=resultdict)
        if not isinstance(result, Result):
            logger.warning(f'AggregateResultdicts ignored invalid input "{resultdict}"')
            continue

        tags = result.tags

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

        for field in fields(result):
            field_dict = getattr(result, field.name)
            for k, v in field_dict.items():
                grouped_resultdicts[tag_tuple][field.name][k].append(v)

    return grouped_resultdicts


def aggregate_resultdicts(inputs, across) -> Tuple[List[Dict], List[Dict]]:
    grouped_resultdicts = group_resultdicts(inputs, across)

    aggregated = list()
    non_aggregated = list()

    for tag_tuple, listdict in grouped_resultdicts.items():
        resultdict: Dict[str, Dict] = defaultdict(dict)
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
                    logger.warning(f'Removing "{f}.{key}={resultdict[f][key]}" from resultdict due to "{validation_errors[f]}"')
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
    across = traits.Str(desc="across which entity to aggregate")


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
