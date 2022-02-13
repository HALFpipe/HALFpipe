# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""


class Context:
    def __init__(self):
        pass

    def serialize(self):
        raise NotImplementedError

    @classmethod
    def deserialize(cls, str):
        raise NotImplementedError
