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
from nipype.interfaces.base import TraitedSpec, traits
from parse import Result as ParseResult
from parse import parse
from pyrsistent import freeze, thaw

from ...utils.ops import check_almost_equal


class ResultdictsOutputSpec(TraitedSpec):
    resultdicts = traits.List(traits.Dict(traits.Str(), traits.Any()))


continuous_format = "{mean:e} ± {std:e} (n = {n_observations:d}, {n_missing:d} missing)"


@dataclass
class Continuous:
    mean: float
    std: float
    n_observations: int
    n_missing: int

    @classmethod
    def load(cls, o: Any) -> Continuous | None:
        if isinstance(o, Continuous):
            return o

        if isinstance(o, Mapping):
            mean = o.get("mean")
            std = o.get("std")
            n_observations = o.get("n_observations")
            n_missing = o.get("n_missing")

            if (
                isinstance(mean, float)
                and isinstance(std, float)
                and isinstance(n_observations, int)
                and isinstance(n_missing, int)
            ):
                return cls(mean, std, n_observations, n_missing)

        elif isinstance(o, str):
            parse_result = parse(continuous_format, o)
            if isinstance(parse_result, ParseResult):
                return cls.load(parse_result.named)

        elif isinstance(o, (float, int, np.number)):
            if isfinite(o):
                return cls(float(o), nan, 1, 0)
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

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Continuous):
            return (
                isclose(self.mean, o.mean)
                and isclose(self.std, o.std)
                and self.n_observations == o.n_observations
                and self.n_missing == o.n_missing
            )
        return False

    @staticmethod
    def summarize(oo: list[Continuous | None]) -> str | float | None:
        uu = list(o.mean for o in oo if o is not None and isfinite(o.mean))
        if len(uu) == 0:
            return None

        v = uu[0]
        if all(isclose(v, u) for u in uu):
            return v

        mean = statistics.mean(uu)
        std = statistics.stdev(uu)
        n_observations = len(oo)
        n_missing = len(oo) - len(uu)

        return str(Continuous(mean, std, n_observations, n_missing))


@dataclass
class Categorical:
    counter: Counter

    @classmethod
    def load(cls, oo: Any) -> Categorical | None:
        if isinstance(oo, Categorical):
            return oo

        elif isinstance(oo, Mapping):
            if isinstance(oo, Counter):
                return cls(oo)

        elif isinstance(oo, Sequence):
            counter: Counter | None = None

            for o in oo:
                if isinstance(o, Categorical):
                    if counter is None:
                        counter = Counter()
                    counter.update(o.counter)

                elif isinstance(o, Mapping):
                    if "value" not in o:
                        break
                    value = o["value"]
                    if not isinstance(value, Hashable):
                        value = freeze(value)

                    count = o.get("count")
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

        if not isinstance(oo, Hashable):
            oo = freeze(oo)

        return cls(Counter([oo]))

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

        if len(count_list) == 1:
            (d,) = count_list
            return d["value"]

        return count_list
