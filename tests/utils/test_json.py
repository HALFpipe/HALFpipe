# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from dataclasses import dataclass
from json import dumps

import numpy as np
import pytest
from halfpipe.utils.json import TypeAwareJSONEncoder
from pyrsistent import pmap


def test_bool():
    x = np.int32(5) > np.int32(6)

    with pytest.raises(TypeError):
        dumps(dict(x=x))

    dumps(dict(x=x), cls=TypeAwareJSONEncoder)


@pytest.mark.parametrize("cls", [np.int32, np.uint32])
def test_int(cls):
    x = cls(5)

    with pytest.raises(TypeError):
        dumps(dict(x=x))

    dumps(dict(x=x), cls=TypeAwareJSONEncoder)


def test_float():
    x = np.float32(5)

    with pytest.raises(TypeError):
        dumps(dict(x=x))

    dumps(dict(x=x), cls=TypeAwareJSONEncoder)


def test_pmap():
    x = pmap(dict(x=5))

    with pytest.raises(TypeError):
        dumps(dict(x=x))

    dumps(dict(x=x), cls=TypeAwareJSONEncoder)


def test_dataclass() -> None:
    @dataclass
    class TestDataclass:
        x: int

    x = TestDataclass(x=5)

    with pytest.raises(TypeError):
        dumps(dict(x=x))

    dumps(dict(x=x), cls=TypeAwareJSONEncoder)

    with pytest.raises(TypeError):
        dumps(dict(x=TestDataclass), cls=TypeAwareJSONEncoder)
