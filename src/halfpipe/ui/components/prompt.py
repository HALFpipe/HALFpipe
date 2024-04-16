# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

""" """


class Prompt:
    def __init__(self):
        pass

    def __call__(self, cntxt):
        raise NotImplementedError

    def __repr__(self):
        raise NotImplementedError
