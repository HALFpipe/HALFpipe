# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..hash import int_digest


def test_int_digest():
    assert int_digest("LR") % 10**4 != int_digest("RL") % 10**4
