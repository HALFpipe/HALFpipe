# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .base import File
from .bids import BidsFileSchema
from .anat import AnatFileSchema, T1wFileSchema
from .func import (
    FuncFileSchema,
    BoldFileSchema,
    TxtEventsFileSchema,
    TsvEventsFileSchema,
    MatEventsFileSchema,
)
from .fmap import (
    FmapFileSchema,
    PhaseFmapFileSchema,
    PhaseDiffFmapFileSchema,
    EPIFmapFileSchema,
    BaseFmapFileSchema,
)
from .ref import RefFileSchema
from .spreadsheet import SpreadsheetFileSchema
from .schema import FileSchema

__all__ = [
    File,
    BidsFileSchema,
    AnatFileSchema,
    T1wFileSchema,
    FuncFileSchema,
    BoldFileSchema,
    TxtEventsFileSchema,
    TsvEventsFileSchema,
    MatEventsFileSchema,
    FmapFileSchema,
    PhaseFmapFileSchema,
    PhaseDiffFmapFileSchema,
    EPIFmapFileSchema,
    BaseFmapFileSchema,
    RefFileSchema,
    SpreadsheetFileSchema,
    FileSchema,
]
