# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""


from marshmallow import (
    fields,
    Schema,
    validate,
    EXCLUDE,
    ValidationError,
    validates_schema,
    pre_load,
)
from inflection import underscore

from .setting import BaseSettingSchema
from .variable import VariableSchema


axis_codes = ["i-", "i", "j-", "j", "k-", "k"]
space_codes = [
    "pa",
    "ap",
    "rl",
    "lr",
    "si",
    "is",
]
direction_codes = [*axis_codes, *space_codes]

slice_order_strs = [
    "sequential increasing",
    "sequential decreasing",
    "alternating increasing even first",
    "alternating increasing odd first",
    "alternating decreasing even first",
    "alternating decreasing odd first",
]

templates = ["MNI152NLin2009cAsym", "MNI152NLin6Asym"]


class BaseMetadataSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    @pre_load
    def underscore_fields(self, in_data, **kwargs):
        return {underscore(k): v for k, v in in_data.items()}


class PEDirMetadataSchema(BaseMetadataSchema):
    phase_encoding_direction = fields.Str(
        validate=validate.OneOf(direction_codes),
        description="The letters i, j, k correspond to the first, second and "
        "third axis of the data in the NIFTI file.",
    )


class TEMetadataSchema(BaseMetadataSchema):
    echo_time = fields.Float(
        description="The echo time (TE) for the acquisition, specified in seconds.",
        unit="seconds",
        validate=validate.Range(min=0.0)
    )


class BoldMetadataSchema(PEDirMetadataSchema, TEMetadataSchema):
    repetition_time = fields.Float(
        description="The time in seconds between the beginning of an acquisition of one "
        "volume and the beginning of acquisition of the volume following it (TR).",
        unit="seconds",
        validate=validate.Range(min=0.0)
    )
    effective_echo_spacing = fields.Float(
        description='The "effective" sampling interval, specified in seconds, between lines '
        "in the phase-encoding direction, defined based on the size of the reconstructed "
        "image in the phase direction.",
        unit="seconds",
        validate=validate.Range(min=0.0)
    )
    slice_timing = fields.List(
        fields.Float(),
        description="A list of times containing the time (in seconds) of each slice acquisition in relation to the beginning of volume acquisition.",
        unit="seconds",
    )
    slice_timing_code = fields.Str(validate=validate.OneOf(slice_order_strs))
    slice_encoding_direction = fields.Str(description="", validate=validate.OneOf(direction_codes))

    @validates_schema
    def validate_slice_timing(self, data, **kwargs):
        if "slice_timing" not in data or "repetition_time" not in data:
            return  # nothing to validate
        if "slice_timing_code" in data and data["slice_timing_code"] is not None:
            raise ValidationError("Cannot specify both slice_timing and slice_timing_code at the same time")
        if isinstance(data["slice_timing"], list):
            if max(data["slice_timing"]) >= data["repetition_time"]:
                raise ValidationError("SliceTiming values must be smaller than RepetitionTime")


class PhaseDiffMetadataSchema(BaseMetadataSchema):
    echo_time_difference = fields.Float(
        description="The echo time difference between the acquisitions, specified in seconds.",
        unit="seconds",
        validate=validate.Range(min=0.0)
    )


class EventsMetadataSchema(BaseMetadataSchema):
    units = fields.Str(
        validate=validate.OneOf(["scans", "seconds"]),
        description="The units in which onsets and durations are specified.",
    )


class RefMetadataSchema(Schema):
    space = fields.Str(
        validate=validate.OneOf(templates),
        description="The space in which the image is provided.",
    )


class SpreadsheetMetadataSchema(Schema):
    variables = fields.List(fields.Nested(VariableSchema), default=[])

    @validates_schema
    def validate_variables(self, data, **kwargs):
        if "variables" not in data:
            return
        names = [c["name"] for c in data["variables"] if "name" in c]
        if len(names) > len(set(names)):
            raise ValidationError("Duplicate variable name")


class ResultdictMetadataSchema(BaseSettingSchema):
    sources = fields.List(fields.Str())
    raw_sources = fields.List(fields.Str())
    sampling_frequency = fields.Float()
    repetition_time = fields.Float()
    skull_stripped = fields.Bool()
    mean_t_s_n_r = fields.Raw()
    coverage = fields.Raw()
    critical_z = fields.Raw()


MetadataSchema = Schema.from_dict(
    {
        k: v
        for schema in [
            PhaseDiffMetadataSchema,
            EventsMetadataSchema,
            RefMetadataSchema,
            BoldMetadataSchema,
        ]
        for k, v in schema().fields.items()
    }
)
