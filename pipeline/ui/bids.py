# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from calamities import TextView, DirectoryInputView, SpacerView, TextElement

from os import path as op

from .step import Step
from .anat import AnatSummaryStep, AnatStep
from ..spec import (
    BIDSAnatTagsSchema,
    BIDSEventsTagsSchema,
    BIDSBoldTagsSchema,
    BIDSFmapTagsSchema,
    File,
)
from .utils import YesNoStep

import marshmallow

from bids import BIDSLayout


def _make_regex_dict(layout, entity_names):
    regex_dict = {
        entity_name: layout.entities[entity_name].regex for entity_name in entity_names
    }
    return regex_dict


def _make_generic_tuple(file_path, generic_regex_dict, other_regex_dict):
    generic_path = ""
    while True:
        entity_name = None
        start = len(file_path)
        end = None
        match = None
        for _entity_name, entity_regex in generic_regex_dict.items():
            _match = entity_regex.search(file_path)
            if _match is not None:
                _start, _end = _match.span(1)
                if _start < start:
                    entity_name = _entity_name
                    start = _start
                    end = _end
                    match = _match
        if match is None:
            break
        generic_path += file_path[:start]
        generic_path += f"{{{entity_name}:[a-zA-Z0-9]}}"
        file_path = file_path[end:]
    generic_path += file_path
    other_tags = []
    for entity_name, entity_regex in other_regex_dict.items():
        match = entity_regex.search(file_path)
        if match is not None:
            other_tags.append((entity_name, match.group(1)))
    return generic_path, tuple(other_tags)


def _load_part(
    ctx, layout, filter, generic_entities, other_entities, metadata_entities, schema
):
    files = layout.get(return_type="filename", **filter)
    generic_regex_dict = _make_regex_dict(layout, generic_entities)
    other_regex_dict = _make_regex_dict(layout, other_entities)
    pattern_set = set(
        (
            *_make_generic_tuple(f, generic_regex_dict, other_regex_dict),
            tuple(
                (k, v)
                for k, v in layout.get_metadata(f).items()
                if k in metadata_entities
            ),
        )
        for f in files
    )
    for path, entity_tags, metadata_tags in pattern_set:
        try:
            tags_dict = dict(entity_tags)
            tags_dict.update(metadata_tags)
            tags_obj = schema.load(tags_dict)
            file_obj = File(path=path, tags=tags_obj)
            ctx.add_file_obj(file_obj)
        except marshmallow.exceptions.ValidationError:
            # unsupported file type
            pass


def _load_bids(ctx, bids_dir):
    layout = BIDSLayout(bids_dir, absolute_paths=True)
    other_entities = ["datatype", "extension", "suffix"]
    _load_part(
        ctx,
        layout,
        {"datatype": "anat", "suffix": "T1w"},
        ["subject"],
        other_entities,
        [],
        BIDSAnatTagsSchema(),
    )
    _load_part(
        ctx,
        layout,
        {"datatype": "func", "suffix": "bold"},
        ["subject", "session", "run", "task"],
        other_entities,
        ["RepetitionTime", "PhaseEncodingDirection", "EffectiveEchoSpacing"],
        BIDSBoldTagsSchema(),
    )
    _load_part(
        ctx,
        layout,
        {"datatype": "func", "suffix": "events", "extension": "tsv"},
        ["subject", "session", "run", "task"],
        other_entities,
        [],
        BIDSEventsTagsSchema(),
    )
    _load_part(
        ctx,
        layout,
        {"datatype": "fmap"},
        ["subject", "session", "run", "task"],
        other_entities,
        ["PhaseEncodingDirection", "EchoTime1", "EchoTime2", "EchoTimeDifference"],
        BIDSFmapTagsSchema(),
    )
    participantsfilepath = op.join(bids_dir, "participants.tsv")
    if op.isfile(participantsfilepath):
        ctx.spreadsheet_file = participantsfilepath


class GetBIDSDirStep(Step):
    def _message(self):
        return self.message

    def setup(self, ctx):
        self._append_view(TextView("Specify BIDS directory"))
        self.message = None
        self.bids_dir_input_view = DirectoryInputView(messagefun=self._message)
        self._append_view(self.bids_dir_input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            bids_dir = self.bids_dir_input_view()
            if bids_dir is None:
                return False
            try:
                _load_bids(ctx, bids_dir)
                self.message = None
                ctx.is_from_bids = True
                return True
            except Exception as e:
                error_color = self.app.layout.color.red
                self.message = TextElement(str(e), color=error_color)

    def next(self, ctx):
        return AnatSummaryStep(self.app)(ctx)


class IsBIDSStep(YesNoStep):
    header_str = "Is the data available in BIDS format?"
    yes_step_type = GetBIDSDirStep
    no_step_type = AnatStep


BIDSStep = IsBIDSStep
