# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .base import ScanTagsSchema, DirTagsSchema, AcqTagsSchema


class FmapTagsSchema(ScanTagsSchema, AcqTagsSchema):
    pass


class EPIFmapTagsSchema(FmapTagsSchema, DirTagsSchema):
    pass


__all__ = [FmapTagsSchema, EPIFmapTagsSchema]
