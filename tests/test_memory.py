# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from halfpipe.memory import memory_limit


def test_memory_limit():
    m = memory_limit()

    assert m > 0
