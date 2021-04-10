# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .func import FuncTagsSchema


class FmapTagsSchema(FuncTagsSchema):
    pass


class EPIFmapTagsSchema(FuncTagsSchema):
    pass


__all__ = [FmapTagsSchema, EPIFmapTagsSchema]
