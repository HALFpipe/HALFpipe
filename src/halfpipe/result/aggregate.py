# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from dataclasses import dataclass
from itertools import chain
from operator import attrgetter
from typing import Any, Mapping

from more_itertools import collapse
from pyrsistent import freeze, pmap, thaw
from tqdm.auto import tqdm

from ..logging import logger
from ..utils.copy import deepcopy
from .base import ResultDict, ResultKey
from .variables import Categorical, Continuous

Index = Mapping[str, str]

source_keys = [
    ("metadata", "sources"),
    ("metadata", "Sources"),
    ("metadata", "raw_sources"),
    ("metadata", "RawSources"),
]


@dataclass(frozen=True)
class Element:
    numerical_index: int
    across_value: str
    data: Mapping[tuple[ResultKey, str], Any]


def group_across(rr: list[ResultDict], across_key: str) -> dict[Index, set[Element]]:
    groups: dict[Index, set[Element]] = defaultdict(set)

    for i, r in enumerate(rr):
        tags = r.pop("tags")
        assert isinstance(tags, dict)

        across_value = str(tags.pop(across_key))

        index = pmap(
            {key: value for key, value in tags.items() if isinstance(value, str)}
        )

        data: Mapping[tuple[ResultKey, str], Any] = pmap(
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
    indices = set(groups.keys())

    expanded_groups: dict[Index, set[Element]] = defaultdict(set)
    for index, elements in groups.items():
        expanded_groups[index] |= elements

    with tqdm(desc="expanding groups", total=len(indices)) as progress_bar:
        while len(indices) > 0:
            target = indices.pop()

            candidates = indices.copy()
            for candidate in candidates:
                if candidate == target:
                    continue

                keys = set(target.keys()).intersection(candidate.keys())
                if not all(candidate[key] == target[key] for key in keys):
                    continue  # candidate is not compatible with target

                index = pmap({key: target[key] for key in keys})
                logger.debug(f"Merging {target} and {candidate} into {index}")

                target_elements = expanded_groups.pop(target)
                candidate_elements = expanded_groups.pop(candidate)

                expanded_groups[index] |= target_elements
                expanded_groups[index] |= candidate_elements

                indices.remove(candidate)
                indices.add(index)

                break

            progress_bar.update()

    return expanded_groups


def merge_data(elements: set[Element]) -> ResultDict:
    # Find all field name attribute name pairs in the set of elements
    keys: set[tuple[ResultKey, str]] = set(
        chain.from_iterable(element.data.keys() for element in elements)
    )

    sorted_elements = sorted(elements, key=attrgetter("numerical_index"))
    result: ResultDict = defaultdict(dict)
    for key in keys:
        values = [element.data.get(key) for element in sorted_elements]
        field_name, attribute_name = key
        if key in source_keys or field_name in ["images"]:
            values = list(collapse(values))

        result[field_name][attribute_name] = thaw(values)

    return result


def aggregate_results(
    rr: list[ResultDict],
    across_key: str,
    summarize_metadata: bool = True,
) -> tuple[list[ResultDict], list[ResultDict]]:
    groups = group_across(rr, across_key)
    expanded_groups = group_expand(groups)

    aggregated: list[ResultDict] = list()
    bypass: list[ResultDict] = list()

    for index, elements in expanded_groups.items():
        tags: dict[str, Any] = {
            across_key: [element.across_value for element in elements]
        }
        tags |= index

        u: ResultDict = {"tags": tags}
        u |= merge_data(elements)

        if len(elements) > 1:
            aggregated.append(u)
        else:
            bypass.append(u)

    return aggregated, bypass


def summarize(values: list[Any]) -> Any:
    """
    Summarizes a list of values, which can be either continuous or categorical.

    Args:
        values (list): A list of values to summarize.

    Returns:
        Any: The summarized value. If all values are continuous, returns a summary of the continuous values, which are the mean and standard deviation as a string.
        If any value is categorical, returns a summary of the categorical values, which are the counts of each level.
    """
    continuous_values = list(map(Continuous.load, values))
    if all(x is None or y is not None for x, y in zip(values, continuous_values)):
        return Continuous.summarize(continuous_values)
    else:
        categorical_values = list(map(Categorical.load, values))
        return Categorical.summarize(categorical_values)


def summarize_metadata(
    result: ResultDict,
) -> ResultDict:
    result = deepcopy(result)
    for field_name, attribute_dict in result.items():
        if field_name in ["images"]:
            continue
        for attribute_name in attribute_dict.keys():
            key = (field_name, attribute_name)
            if key in source_keys:
                continue
            attribute_dict[attribute_name] = summarize(attribute_dict[attribute_name])
    return result
