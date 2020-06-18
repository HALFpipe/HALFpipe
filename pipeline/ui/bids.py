# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from calamities import TextView, DirectoryInputView, SpacerView, TextElement

import logging
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
from ..utils import first

import marshmallow

from bids import BIDSLayout
from sdcflows.interfaces.fmap import get_ees


def _make_regex_dict(layout, entity_names):
    regex_dict = {entity_name: layout.entities[entity_name].regex for entity_name in entity_names}
    return regex_dict


def _get_metadata_tuple(fname, metadata_entities, layout):
    metadata = layout.get_metadata(fname)
    if "EffectiveEchoSpacing" in metadata_entities and "EffectiveEchoSpacing" not in metadata:
        try:
            # get effective echo spacing even if not explicitly specified
            metadata["EffectiveEchoSpacing"] = get_ees(metadata, in_file=fname)
        except Exception:
            pass
    if "EchoTimeDifference" in metadata_entities and "EchoTimeDifference" not in metadata:
        if "EchoTime1" in metadata and "EchoTime2" in metadata:
            metadata["EchoTimeDifference"] = abs(
                float(metadata["EchoTime1"]) - float(metadata["EchoTime2"])
            )
    return tuple((k, v) for k, v in metadata.items() if k in metadata_entities)


def _make_generic_path(file_path, regex_dict):
    generic_path = ""
    entities_in_path = set()
    while True:
        entity_name = None
        start = len(file_path)
        end = None
        match = None
        for _entity_name, entity_regex in regex_dict.items():
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
        entities_in_path.add(entity_name)
        file_path = file_path[end:]
    generic_path += file_path
    return generic_path, entities_in_path


def _get_tags_tuple(file_path, regex_dict):
    other_tags = []
    for entity_name, entity_regex in regex_dict.items():
        match = entity_regex.search(file_path)
        if match is not None:
            other_tags.append((entity_name, match.group(1)))
    return tuple(other_tags)


def _get_pattern_set(layout, filepaths, generic_entities, other_entities, metadata_entities):
    generic_regex_dict = _make_regex_dict(layout, generic_entities)
    other_regex_dict = _make_regex_dict(layout, other_entities)
    pattern_set = set()
    for filepath in filepaths:
        generic_path, _ = _make_generic_path(filepath, generic_regex_dict)
        other_tags_tuple = _get_tags_tuple(filepath, other_regex_dict)
        metadata_tags_tuple = _get_metadata_tuple(filepath, metadata_entities, layout)
        pattern_set.add((generic_path, other_tags_tuple, metadata_tags_tuple))
    return pattern_set


def _get_fmap_pattern_set(layout, funcfiles, generic_entities, other_entities, metadata_entities):
    generic_regex_dict = _make_regex_dict(layout, generic_entities)
    other_regex_dict = _make_regex_dict(layout, other_entities)

    funcfile_by_fmapfile = {}
    entitydict_by_funcfile = {}
    for funcfile in funcfiles:
        funcfile_entitydict = layout.get_file(funcfile).get_entities()
        funcfile_entitydict = {
            k: v for k, v in funcfile_entitydict.items() if k in generic_entities
        }
        entitydict_by_funcfile[funcfile] = funcfile_entitydict
        fmapslist = layout.get_fieldmap(funcfile, return_list=True)
        for fmaps in fmapslist:
            for fmapfile in fmaps.values():
                if not op.isfile(fmapfile):
                    continue
                if fmapfile not in funcfile_by_fmapfile:
                    funcfile_by_fmapfile[fmapfile] = set()
                funcfile_by_fmapfile[fmapfile].add(funcfile)

    pattern_set = set()
    for fmapfile, funcfileset in funcfile_by_fmapfile.items():
        # create set of values for each entity across associated bold files
        valset_by_entity = {}
        for funcfile in funcfileset:
            for k, v in entitydict_by_funcfile[funcfile].items():
                if k not in valset_by_entity:
                    valset_by_entity[k] = set()
                valset_by_entity[k].add(v)
        # get entities of the fmap file
        fmapfile_entitydict = layout.get_file(fmapfile).get_entities()
        # select entities that we identify an fmap file by
        entityvals = {
            entity: first(valset)
            for entity, valset in valset_by_entity.items()
            if len(valset) == 1  # has a constant value across all associated bold files
            and entity in generic_entities  # is one we actually want to make generic
        }
        # we can only make entities generic in the file name that are actually constant
        # across both the associated bold files and the fmap file
        regex_dict = {
            entity: v
            for entity, v in generic_regex_dict.items()
            if entity in entityvals  # is constant across associated bold files
            and entity in fmapfile_entitydict  # defined for fmap file
            and fmapfile_entitydict[entity] == entityvals[entity]  # the same for fmap file
        }
        generic_path, entities_in_path = _make_generic_path(fmapfile, regex_dict)
        # other tags
        other_tags_tuple = _get_tags_tuple(fmapfile, other_regex_dict)
        other_tags_tuple = (
            *other_tags_tuple,
            *(
                (entity, val)
                for entity, val in entityvals.items()
                if entity not in entities_in_path
            ),
        )
        metadata_tags_tuple = _get_metadata_tuple(fmapfile, metadata_entities, layout)
        pattern_set.add((generic_path, other_tags_tuple, metadata_tags_tuple))
    return pattern_set


def _load_part(ctx, schema, pattern_set):
    # add a file object for every pattern extracted from the bids spec
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

    # load

    anatfiles = layout.get(return_type="filename", datatype="anat", suffix="T1w")
    anat_pattern_set = _get_pattern_set(layout, anatfiles, ["subject"], other_entities, [],)
    _load_part(ctx, BIDSAnatTagsSchema(), anat_pattern_set)

    funcfiles = layout.get(return_type="filename", datatype="func", suffix="bold")
    func_pattern_set = _get_pattern_set(
        layout,
        funcfiles,
        ["subject", "session", "run", "task"],
        other_entities,
        ["RepetitionTime", "PhaseEncodingDirection", "EffectiveEchoSpacing"],
    )
    _load_part(ctx, BIDSBoldTagsSchema(), func_pattern_set)

    eventfiles = layout.get(
        return_type="filename", datatype="func", suffix="events", extension="tsv"
    )
    events_pattern_set = _get_pattern_set(
        layout, eventfiles, ["subject", "session", "run", "task"], other_entities, [],
    )
    _load_part(ctx, BIDSEventsTagsSchema(), events_pattern_set)

    fmap_pattern_set = _get_fmap_pattern_set(
        layout,
        funcfiles,
        ["subject", "session", "run", "task"],
        other_entities,
        ["PhaseEncodingDirection", "EchoTimeDifference", "EchoTime"],
    )
    _load_part(ctx, BIDSFmapTagsSchema(), fmap_pattern_set)

    participantsfilepath = op.join(bids_dir, "participants.tsv")
    if op.isfile(participantsfilepath):
        ctx.spreadsheet_file = participantsfilepath

    # validate

    funcfiles = ctx.database.get(
        datatype="func", suffix="bold"
    )  # only validate files that made it to the database
    for funcfile in funcfiles:
        bidsfmapset = set()
        fmapslist = layout.get_fieldmap(funcfile, return_list=True)
        for fmaps in fmapslist:
            for fmapfile in fmaps.values():
                if not op.isfile(fmapfile):
                    continue
                bidsfmapset.add(fmapfile)
        fmapfiles = ctx.database.get_associations(funcfile, datatype="fmap")
        if fmapfiles is not None:
            specfmapset = set(fmapfiles)
            assert bidsfmapset == specfmapset, "Inconsistent FieldMap specification"


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
                logging.getLogger("pipeline.ui").exception("Exception: %s", e)
                error_color = self.app.layout.color.red
                self.message = TextElement(str(e), color=error_color)

    def next(self, ctx):
        return AnatSummaryStep(self.app)(ctx)


class IsBIDSStep(YesNoStep):
    header_str = "Is the data available in BIDS format?"
    yes_step_type = GetBIDSDirStep
    no_step_type = AnatStep


BIDSStep = IsBIDSStep
