# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .anat import AnatFileSchema, T1wFileSchema
from .base import File
from .bids import BidsFileSchema
from .fmap import (
    BaseFmapFileSchema,
    EPIFmapFileSchema,
    FmapFileSchema,
    PhaseDiffFmapFileSchema,
    PhaseFmapFileSchema,
)
from .func import (
    BoldFileSchema,
    FuncFileSchema,
    MatEventsFileSchema,
    TsvEventsFileSchema,
    TxtEventsFileSchema,
)
from .ref import RefFileSchema
from .schema import FileSchema
from .spreadsheet import SpreadsheetFileSchema

__all__ = [
    "File",
    "BidsFileSchema",
    "AnatFileSchema",
    "T1wFileSchema",
    "FuncFileSchema",
    "BoldFileSchema",
    "TxtEventsFileSchema",
    "TsvEventsFileSchema",
    "MatEventsFileSchema",
    "FmapFileSchema",
    "PhaseFmapFileSchema",
    "PhaseDiffFmapFileSchema",
    "EPIFmapFileSchema",
    "BaseFmapFileSchema",
    "RefFileSchema",
    "SpreadsheetFileSchema",
    "FileSchema",
]
