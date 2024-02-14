# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from dataclasses import dataclass
from itertools import chain
from operator import attrgetter
from typing import Any, Iterable, Mapping

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


def group_across(results: list[ResultDict], across_key: str) -> dict[Index, set[Element]]:
    groups: dict[Index, set[Element]] = defaultdict(set)

    for i, result in enumerate(results):
        tags = result["tags"]
        result["tags"] = dict()

        if not isinstance(tags, dict):
            raise ValueError("Tags must be a dictionary")

        across_value = tags.pop(across_key)
        if not isinstance(across_value, str):
            if isinstance(across_value, list) and len(across_value) == 1:
                across_value = across_value[0]
        if not isinstance(across_value, str):
            raise ValueError(f'Expected "{across_key}" value to be a string, got "{across_value}" instead')

        index = pmap({key: value for key, value in tags.items() if isinstance(value, str)})

        data_dict = {
            (field_name, attribute_name): freeze(attribute_value)
            for field_name, field_dict in result.items()
            for attribute_name, attribute_value in field_dict.items()
        }
        data: Mapping[tuple[ResultKey, str], Any] = pmap(data_dict)

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


def merge_data(elements: Iterable[Element]) -> ResultDict:
    # Find all field name attribute name pairs in the set of elements
    keys: set[tuple[ResultKey, str]] = set(chain.from_iterable(element.data.keys() for element in elements))

    sorted_elements = sorted(elements, key=attrgetter("numerical_index"))
    result: ResultDict = {
        "tags": dict(),
        "images": dict(),
        "vals": dict(),
        "metadata": dict(),
    }
    for key in keys:
        values = [element.data.get(key) for element in sorted_elements]
        field_name, attribute_name = key
        if key in source_keys or field_name in ["images"]:
            values = list(collapse(values))

        result[field_name][attribute_name] = thaw(values)

    return result


def aggregate_results(
    results: list[ResultDict],
    across_key: str,
) -> tuple[list[ResultDict], list[ResultDict]]:
    results_with_across_key: list[ResultDict] = list()
    results_without_across_key: list[ResultDict] = list()
    for result in results:
        if across_key in result["tags"]:
            results_with_across_key.append(result)
        else:
            results_without_across_key.append(result)

    groups = group_across(results_with_across_key, across_key)
    expanded_groups = group_expand(groups)

    aggregated_results: list[ResultDict] = list()
    other_results: list[ResultDict] = list()
    for index, elements in expanded_groups.items():
        sorted_elements = sorted(elements, key=attrgetter("numerical_index"))
        tags: dict[str, Any] = {across_key: [element.across_value for element in sorted_elements]}
        tags |= index
        u = merge_data(sorted_elements)
        u["tags"] |= tags

        if len(elements) > 1:
            aggregated_results.append(u)
        else:
            other_results.append(u)

    other_results.extend(results_without_across_key)

    return aggregated_results, other_results


def summarize(values: list[Any]) -> Any:
    """
    Summarizes a list of values, which can be either continuous or categorical.

    Args:
        values (list): A list of values to summarize.

    Returns:
        Any: The summarized value. If all values are continuous, returns a summary of the continuous values,
        which are the mean and standard deviation as a string. If any value is categorical, returns a summary
        of the categorical values, which are the counts of each level.
    """
    continuous_values = list(map(Continuous.load, values))
    if all(x is None or y is not None for x, y in zip(values, continuous_values, strict=False)):
        return Continuous.summarize(continuous_values)
    else:
        categorical_values = list(map(Categorical.load, values))
        return Categorical.summarize(categorical_values)


def summarize_metadata(
    result: ResultDict,
) -> ResultDict:
    result = deepcopy(result)
    for field_name, attribute_dict in result.items():
        if field_name in ["tags", "images"]:
            continue
        if not isinstance(attribute_dict, dict):
            raise ValueError("Expected attribute_dict to be a dict")
        for attribute_name in attribute_dict.keys():
            key = (field_name, attribute_name)
            if key in source_keys:
                continue
            value = attribute_dict[attribute_name]
            if not isinstance(value, list):
                continue
            attribute_dict[attribute_name] = summarize(value)
    return result
