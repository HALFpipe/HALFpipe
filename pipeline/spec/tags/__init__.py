# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .base import Tags, entity_colors
from .schema import TagsSchema
from .anat import AnatTagsSchema
from .func import (
    FuncTagsSchema,
    BoldTagsSchema,
    EventsTagsSchema,
)
from .fmap import (
    PEPOLARTagsSchema,
    PhaseDifferenceTagsSchema,
    Phase1TagsSchema,
    Phase2TagsSchema,
    Magnitude1TagsSchema,
    Magnitude2TagsSchema,
    FieldMapTagsSchema,
    FmapTagsSchema,
)
from .derivative import (
    SmoothedTagSchema,
    SmoothedTag,
    BandPassFilteredTagSchema,
    BandPassFilteredTag,
    ConfoundsRemovedTag,
    ConfoundsRemovedTagSchema,
)
from .other import AtlasTagsSchema, SeedTagsSchema, MapTag, MapTagsSchema

__all__ = [
    Tags,
    entity_colors,
    TagsSchema,
    AnatTagsSchema,
    FuncTagsSchema,
    BoldTagsSchema,
    EventsTagsSchema,
    PEPOLARTagsSchema,
    PhaseDifferenceTagsSchema,
    Phase1TagsSchema,
    Phase2TagsSchema,
    Magnitude1TagsSchema,
    Magnitude2TagsSchema,
    FieldMapTagsSchema,
    FmapTagsSchema,
    SmoothedTagSchema,
    SmoothedTag,
    BandPassFilteredTagSchema,
    BandPassFilteredTag,
    ConfoundsRemovedTag,
    ConfoundsRemovedTagSchema,
    AtlasTagsSchema,
    SeedTagsSchema,
    MapTag,
    MapTagsSchema,
]
