# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass
from math import isclose, isfinite, nan
from typing import Any, Hashable, Mapping, Sequence

import numpy as np
from parse import Result as ParseResult
from parse import parse
from pyrsistent import freeze, thaw

from ..utils.ops import check_almost_equal

continuous_format = "{mean:e} ± {std:e} (n = {n_observations:d}, {n_missing:d} missing)"


@dataclass
class Continuous:
    mean: float
    std: float
    n_observations: int
    n_missing: int

    @classmethod
    def load(cls, obj: Any) -> Continuous | None:
        if isinstance(obj, Continuous):
            return obj

        if isinstance(obj, Mapping):
            mean = obj.get("mean")
            std = obj.get("std")
            n_observations = obj.get("n_observations")
            n_missing = obj.get("n_missing")

            if (
                isinstance(mean, (float, int))
                and isinstance(std, (float, int))
                and isinstance(n_observations, int)
                and isinstance(n_missing, int)
            ):
                return cls(mean, std, n_observations, n_missing)

        elif isinstance(obj, str):
            parse_result = parse(continuous_format, obj)
            if isinstance(parse_result, ParseResult):
                return cls.load(parse_result.named)

        elif isinstance(obj, (float, int, np.number)):
            if isfinite(obj):
                return cls(float(obj), nan, 1, 0)
            else:
                return cls(nan, nan, 0, 1)

        return None

    def __str__(self) -> str:
        return continuous_format.format(
            mean=self.mean,
            std=self.std,
            n_observations=self.n_observations,
            n_missing=self.n_missing,
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Continuous):
            return (
                isclose(self.mean, other.mean)
                and isclose(self.std, other.std)
                and self.n_observations == other.n_observations
                and self.n_missing == other.n_missing
            )
        return False

    @staticmethod
    def summarize(values: list[Continuous | None]) -> str | float | None:
        means = list(value.mean for value in values if value is not None and isfinite(value.mean))
        if len(means) == 0:
            return None
        elif len(means) == 1:
            (mean,) = means
            return mean

        mean = statistics.mean(means)
        std = statistics.stdev(means)
        n_observations = len(values)
        n_missing = len(values) - len(means)

        return str(Continuous(mean, std, n_observations, n_missing))


@dataclass
class Categorical:
    counter: Counter

    @classmethod
    def load(cls, objects: Any) -> Categorical | None:
        if isinstance(objects, Categorical):
            return objects

        elif isinstance(objects, Mapping):
            if isinstance(objects, Counter):
                return cls(objects)

        elif isinstance(objects, Sequence):
            counter: Counter | None = None

            for obj in objects:
                if isinstance(obj, Categorical):
                    if counter is None:
                        counter = Counter()
                    counter.update(obj.counter)

                elif isinstance(obj, Mapping):
                    if "value" not in obj:
                        break
                    value = obj["value"]
                    if not isinstance(value, Hashable):
                        value = freeze(value)

                    count = obj.get("count")
                    if not isinstance(count, int):
                        break

                    if counter is None:
                        counter = Counter()
                    counter.update({value: count})
                else:
                    counter = None
                    break

            if counter is not None:
                return cls(counter)

        if not isinstance(objects, Hashable):
            objects = freeze(objects)

        return cls(Counter([objects]))

    @staticmethod
    def summarize(oo: list[Categorical | None]) -> Any | None:
        counter: Counter = Counter()

        for o in oo:
            if isinstance(o, Categorical):
                counter.update(o.counter)
            else:
                counter.update({o: 1})

        values = list(counter.keys())

        count_list: list[dict[str, Any]] = list()

        seen: set[Hashable] = set()
        for a in values:
            if a in seen:
                continue

            merge = set(b for b in values if check_almost_equal(a, b)) - seen

            count = sum(counter[b] for b in merge)
            count_list.append(dict(value=thaw(a), count=count))

            seen.update(merge)

        return count_list
