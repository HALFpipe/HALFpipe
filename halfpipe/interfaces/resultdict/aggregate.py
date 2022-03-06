# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from dataclasses import dataclass
from itertools import chain
from operator import attrgetter
from typing import Any, Mapping

from more_itertools import collapse, powerset
from nipype.interfaces.base import BaseInterfaceInputSpec, DynamicTraitedSpec, traits
from nipype.interfaces.io import IOBase, add_traits
from pyrsistent import freeze, pmap, thaw

from ...utils.ops import ravel
from .base import Categorical, Continuous, ResultdictsOutputSpec

Index = Mapping[str, str]


@dataclass(frozen=True)
class Element:
    numerical_index: int
    across_value: str
    data: Mapping[tuple[str, str], Any]


def compare_index(a: Index, b: Index) -> bool:
    intersection_keys = set(a.keys()) & set(b.keys())
    for key in intersection_keys:
        if a[key] != b[key]:
            return False

    return True


def group_across(
    rr: list[dict[str, dict]], across_key: str
) -> dict[Index, set[Element]]:
    groups: dict[Index, set[Element]] = defaultdict(set)

    for i, r in enumerate(rr):
        tags = r.pop("tags")
        assert isinstance(tags, dict)

        across_value = str(tags.pop(across_key))

        index = pmap(
            {key: value for key, value in tags.items() if isinstance(value, str)}
        )

        data: Mapping[tuple[str, str], Any] = pmap(
            {
                (field_name, attribute_name): freeze(attribute_value)
                for field_name, field_dict in r.items()
                for attribute_name, attribute_value in field_dict.items()
            }
        )

        element = Element(i, across_value, data)

        groups[index].add(element)

    return groups


def group_expand(groups: dict[Index, set[Element]]) -> dict[Index, set[Element]]:
    expanded_groups: dict[Index, set[Element]] = dict()

    indices = set(groups.keys())
    consumed_indices: set[Index] = set()
    for aa in powerset(indices):  # potential bottleneck
        if len(aa) == 0:
            continue

        keys = [set(a.keys()) for a in aa]
        intersection_keys = set.intersection(*keys)

        if any(len(set(a[key] for a in aa)) > 1 for key in intersection_keys):
            continue  # conflicting tags

        a = next(iter(aa))
        index = pmap((key, a[key]) for key in intersection_keys)
        elements = set(chain.from_iterable(groups[a] for a in aa))

        if index not in expanded_groups or len(elements) > len(expanded_groups[index]):
            for a in aa:
                if a != index:
                    consumed_indices.add(a)

            expanded_groups[index] = elements

    for a in consumed_indices:
        del expanded_groups[a]

    return expanded_groups


def summarize(xx: list[Any]) -> Any:
    continuous_values = list(map(Continuous.load, xx))
    if all(x is None or y is not None for x, y in zip(xx, continuous_values)):
        return Continuous.summarize(continuous_values)
    else:
        categorical_values = list(map(Categorical.load, xx))
        return Categorical.summarize(categorical_values)


def merge_data(elements: set[Element]) -> dict[str, dict[str, Any]]:
    keys = set(chain.from_iterable(element.data.keys() for element in elements))

    sorted_elements = sorted(elements, key=attrgetter("numerical_index"))
    summarized: dict[tuple[str, str], Any] = dict()
    for key in keys:
        values = [element.data.get(key) for element in sorted_elements]
        field_name, _ = key
        if key in [
            ("metadata", "sources"),
            ("metadata", "raw_sources"),
        ] or field_name in ["images"]:
            summarized[key] = list(collapse(values))
        else:
            summarized[key] = summarize(values)

    data: dict[str, dict[str, Any]] = defaultdict(dict)
    for (field_name, attribute_name), attribute_value in summarized.items():
        data[field_name][attribute_name] = thaw(attribute_value)

    return data


def aggregate(rr: list[dict[str, dict]], across_key: str):
    groups = group_across(rr, across_key)
    expanded_groups = group_expand(groups)

    aggregated: list[dict[str, dict[str, Any]]] = list()
    bypass: list[dict[str, dict[str, Any]]] = list()

    for index, elements in expanded_groups.items():
        tags: dict[str, Any] = {
            across_key: [element.across_value for element in elements]
        }
        tags |= index

        u: dict[str, dict[str, Any]] = dict(tags=tags) | merge_data(elements)

        if len(elements) > 1:
            aggregated.append(u)
        else:
            bypass.append(u)

    return aggregated, bypass


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

        inputs = ravel(
            [getattr(self.inputs, input_name) for input_name in self.input_names]
        )
        across = self.inputs.across

        aggregated, non_aggregated = aggregate(inputs, across)

        outputs["resultdicts"] = aggregated
        outputs["non_aggregated_resultdicts"] = non_aggregated

        return outputs
