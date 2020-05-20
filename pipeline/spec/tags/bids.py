# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from inflection import camelize

from marshmallow import pre_load

from .anat import AnatTagsSchema
from .func import BoldTagsSchema, EventsTagsSchema
from .fmap import (
    FmapTagsSchema,
    PEPOLARTagsSchema,
    PhaseDifferenceTagsSchema,
    Phase1TagsSchema,
    Phase2TagsSchema,
    Magnitude1TagsSchema,
    Magnitude2TagsSchema,
    FieldMapTagsSchema,
)

metadata_fields = [
    "phase_encoding_direction",
    "echo_time",
    "echo_time_1",
    "echo_time_2",
    "echo_time_difference",
    "repetition_time",
    "effective_echo_spacing",
]


class BIDSMixin:
    @pre_load
    def uncamelize_fields(self, in_data, **kwargs):
        for field in metadata_fields:
            camelized_field = camelize(field)
            if camelized_field in in_data:
                in_data[field] = in_data[camelized_field]
                del in_data[camelized_field]
        return in_data


class BIDSAnatTagsSchema(BIDSMixin, AnatTagsSchema):
    pass


class BIDSBoldTagsSchema(BIDSMixin, BoldTagsSchema):
    pass


class BIDSEventsTagsSchema(BIDSMixin, EventsTagsSchema):
    pass


class BIDSFmapTagsSchema(FmapTagsSchema):
    class BIDSPEPOLARTagsSchema(BIDSMixin, PEPOLARTagsSchema):
        pass

    class BIDSPhaseDifferenceTagsSchema(BIDSMixin, PhaseDifferenceTagsSchema):
        pass

    class BIDSPhase1TagsSchema(BIDSMixin, Phase1TagsSchema):
        pass

    class BIDSPhase2TagsSchema(BIDSMixin, Phase2TagsSchema):
        pass

    class BIDSMagnitude1TagsSchema(BIDSMixin, Magnitude1TagsSchema):
        pass

    class BIDSMagnitude2TagsSchema(BIDSMixin, Magnitude2TagsSchema):
        pass

    class BIDSFieldMapTagsSchema(BIDSMixin, FieldMapTagsSchema):
        pass

    type_schemas = {
        "phasediff": BIDSPhaseDifferenceTagsSchema,
        "phase1": BIDSPhase1TagsSchema,
        "phase2": BIDSPhase2TagsSchema,
        "magnitude1": BIDSMagnitude1TagsSchema,
        "magnitude2": BIDSMagnitude2TagsSchema,
        "fieldmap": BIDSFieldMapTagsSchema,
        "epi": BIDSPEPOLARTagsSchema,
    }
