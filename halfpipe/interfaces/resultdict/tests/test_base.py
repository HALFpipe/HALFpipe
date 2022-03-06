# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose, nan

from ..base import Continuous


def test_continuous():
    x = list(map(Continuous.load, [0.5, 1.0, 1.5, nan]))
    s = Continuous.summarize(x)
    c = Continuous.load(s)

    assert isinstance(c, Continuous)
    assert isclose(c.mean, 1)
    assert isclose(c.std, 0.5)
    assert c.n_observations == 4
    assert c.n_missing == 1

    s = Continuous.summarize([c, c])
    assert isinstance(s, float) and isclose(s, 1)

    d = Continuous.load(2.0)
    s = Continuous.summarize([c, d])
    c = Continuous.load(s)

    assert isinstance(c, Continuous)
    assert isclose(c.mean, 1.5)
