# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import OrderedDict
from dataclasses import asdict, is_dataclass
from json import JSONEncoder
from pathlib import Path
from typing import Any, Mapping, Optional

import numpy as np


class TypeAwareJSONEncoder(JSONEncoder):
    """
    adapted from https://github.com/illagrenan/django-numpy-json-encoder
    """

    def default(self, o: Any) -> Any:
        if is_dataclass(o):
            o = asdict(o, dict_factory=OrderedDict)  # type: ignore

        if isinstance(o, Mapping):
            if not isinstance(o, dict):
                o = dict(o)
            return o

        if isinstance(o, np.ndarray):
            return o.tolist()

        if isinstance(o, Path):
            return str(o)

        dtype = getattr(o, "dtype", None)
        kind: Optional[str] = getattr(dtype, "kind", None)

        if kind == "b":
            return bool(o)

        elif kind in ["i", "u"]:
            return int(o)

        elif kind == "f":
            return float(o)

        else:
            return super().default(o)
