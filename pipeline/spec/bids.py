# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from inflection import camelize

from marshmallow import EXCLUDE

from .tags import AnatTagsSchema, BoldTagsSchema, EventsTagsSchema, FmapTagsSchema

metadata_fields = [
    "phase_encoding_direction",
    "echo_time_1",
    "echo_time_2",
    "echo_time_difference",
    "repetition_time",
    "effective_echo_spacing",
]


class BIDSMixin:
    class Meta:
        unknown = EXCLUDE

    def on_bind_field(self, field_name, field_obj):
        _field_name = field_obj.data_key or field_name
        if _field_name in metadata_fields:
            field_obj.data_key = camelize(_field_name)


class BIDSAnatTagsSchema(BIDSMixin, AnatTagsSchema):
    pass


class BIDSBoldTagsSchema(BIDSMixin, BoldTagsSchema):
    pass


class BIDSEventsTagsSchema(BIDSMixin, EventsTagsSchema):
    pass


class BIDSFmapTagsSchema(BIDSMixin, FmapTagsSchema):
    pass
