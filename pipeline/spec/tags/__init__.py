# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .base import Tags, entity_colors, tagnames
from .bids import (
    BIDSAnatTagsSchema,
    BIDSEventsTagsSchema,
    BIDSBoldTagsSchema,
    BIDSFmapTagsSchema,
)
from .schema import TagsSchema
from .anat import AnatTagsSchema
from .func import (
    FuncTagsSchema,
    BoldTagsSchema,
    PreprocessedBoldTagsSchema,
    EventsTagsSchema,
    study_entities,
    bold_entities,
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
    derivative_entities,
)
from .other import AtlasTagsSchema, SeedTagsSchema, MapTag, MapTagsSchema

__all__ = [
    Tags,
    entity_colors,
    tagnames,
    BIDSAnatTagsSchema,
    BIDSEventsTagsSchema,
    BIDSBoldTagsSchema,
    BIDSFmapTagsSchema,
    TagsSchema,
    AnatTagsSchema,
    FuncTagsSchema,
    BoldTagsSchema,
    PreprocessedBoldTagsSchema,
    EventsTagsSchema,
    study_entities,
    bold_entities,
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
    derivative_entities,
    AtlasTagsSchema,
    SeedTagsSchema,
    MapTag,
    MapTagsSchema,
]
