# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional

from json import JSONEncoder

import numpy as np
from frozendict import frozendict   # type: ignore


class TypeAwareJSONEncoder(JSONEncoder):
    """
    adapted from https://github.com/illagrenan/django-numpy-json-encoder
    """

    def default(self, o):
        if isinstance(o, frozendict):
            return dict(o)

        if isinstance(o, np.ndarray):
            return o.tolist()

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
