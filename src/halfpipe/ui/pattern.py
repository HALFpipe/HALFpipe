# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from typing import ClassVar, Dict, List, Optional, Type, Union

from ..ingest.glob import get_entities_in_path, tag_parse
from ..model.file.base import BaseFileSchema, File
from ..model.file.schema import FileSchema
from ..model.tags import entities
from ..model.tags import entity_longnames as entity_display_aliases
from ..model.utils import get_schema_entities
from ..utils.format import inflect_engine as p
from ..utils.path import split_ext
from .components import (
    FilePatternInputView,
    SpacerView,
    TextElement,
    TextInputView,
    TextView,
)
from .step import Context, Step
from .utils import entity_colors, forbidden_chars, messagefun

logger = logging.getLogger("halfpipe.ui")


class FilePatternSummaryStep(Step):
    entity_display_aliases: ClassVar[Dict] = entity_display_aliases

    filetype_str: ClassVar[str] = "file"
    filedict: Dict[str, str] = dict()
    schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema

    next_step_type: Optional[Type[Step]] = None

    def setup(self, ctx):
        self.is_first_run = True

        entities = get_schema_entities(self.schema)

        filepaths = ctx.database.get(**self.filedict)
        message = messagefun(
            ctx.database,
            self.filetype_str,
            filepaths,
            entities,
            self.entity_display_aliases,
        )

        self._append_view(TextView(message))
        self._append_view(SpacerView(1))

    def run(self, _):
        return self.is_first_run

    def next(self, ctx):
        if self.is_first_run:
            self.is_first_run = False
            assert self.next_step_type is not None
            return self.next_step_type(self.app)(ctx)
        else:
            return


class AskForMissingEntities(Step):
    def __init__(
        self,
        app,
        entity_display_aliases,
        ask_if_missing_entities,
        suggest_file_stem,
        next_step_type,
    ):
        super(AskForMissingEntities, self).__init__(app)

        self.entity_display_aliases = entity_display_aliases
        self.ask_if_missing_entities = ask_if_missing_entities
        self.suggest_file_stem = suggest_file_stem

        self.entity = None
        self.entity_str = None
        self.tagval = None

        self.next_step_type = next_step_type

    def setup(self, ctx):
        self.is_first_run = True

        entites_in_path = get_entities_in_path(ctx.spec.files[-1].path)

        tags = ctx.spec.files[-1].tags
        while len(self.ask_if_missing_entities) > 0:
            entity = self.ask_if_missing_entities.pop(0)

            if entity in entites_in_path:
                continue

            if tags.get(entity) is not None:
                continue

            self.entity = entity
            break

        if self.entity is not None:
            self.entity_str = self.entity
            if self.entity_str in self.entity_display_aliases:
                self.entity_str = self.entity_display_aliases[self.entity_str]

            self._append_view(TextView(f"No {self.entity_str} name was specified"))
            self._append_view(TextView(f"Specify the {self.entity_str} name"))

            suggestion = ""
            if self.suggest_file_stem:
                suggestion, _ = split_ext(ctx.spec.files[-1].path)

            self.input_view = TextInputView(
                text=suggestion,
                isokfun=lambda text: len(text) > 0 and forbidden_chars.search(text) is None,
            )

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, _):
        if self.entity is None:
            return self.is_first_run
        else:
            self.tagval = self.input_view()
            if self.tagval is None:
                return False
            return True

    def next(self, ctx):
        if self.tagval is not None:
            ctx.spec.files[-1].tags[self.entity] = self.tagval

        if self.entity is not None or self.is_first_run:
            self.is_first_run = False

            if len(self.ask_if_missing_entities) > 0:
                return AskForMissingEntities(
                    self.app,
                    {**self.entity_display_aliases},
                    [*self.ask_if_missing_entities],
                    self.suggest_file_stem,
                    self.next_step_type,
                )(ctx)

            else:
                ctx.database.put(ctx.spec.files[-1])  # we've got all tags, so we can add the fileobj to the index

                return self.next_step_type(self.app)(ctx)


class FilePatternStep(Step):
    suggest_file_stem = False
    entity_display_aliases = entity_display_aliases

    header_str: ClassVar[Optional[str]] = None

    filetype_str = "file"
    filedict: Dict[str, str] = dict()
    schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema

    ask_if_missing_entities: List[str] = list()
    required_in_path_entities: List[str] = list()

    next_step_type: Type[Step]

    def _transform_extension(self, ext):
        return ext

    def setup(self, ctx: Context) -> None:
        self.fileobj: File | None = None

        if hasattr(self, "header_str") and self.header_str is not None:
            self._append_view(TextView(self.header_str))
            self._append_view(SpacerView(1))

        self._append_view(TextView(f"Specify the path of the {self.filetype_str} files"))

        schema_entities = get_schema_entities(self.schema)
        schema_entities = [entity for entity in reversed(entities) if entity in schema_entities]  # keep order

        # need original entities for this
        entity_colors_list = [entity_colors[entity] for entity in schema_entities]

        # convert to display
        schema_entities = [
            (self.entity_display_aliases[entity] if entity in self.entity_display_aliases else entity)
            for entity in schema_entities
        ]

        required_entities = [
            *self.ask_if_missing_entities,
            *self.required_in_path_entities,
        ]

        entity_instruction_strs = []
        optional_entity_strs = []
        for entity in schema_entities:
            if entity in required_entities:
                entity_instruction_strs.append(f"Put {{{entity}}} in place of the {entity} names")
            else:
                optional_entity_strs.append(f"{{{entity}}}")

        if len(optional_entity_strs) > 0:
            entity_instruction_strs.append(f"You can also use {p.join(optional_entity_strs)}")

        entity_instruction_views = [TextView("") for _ in entity_instruction_strs]
        for view in entity_instruction_views:
            self._append_view(view)

        self.input_view = FilePatternInputView(
            schema_entities,
            entity_colors_list=entity_colors_list,
            required_entities=self.required_in_path_entities,
        )
        self._append_view(self.input_view)

        for str, view in zip(entity_instruction_strs, entity_instruction_views, strict=False):
            view.text = self.input_view._tokenize(str, add_brackets=False)

        self._append_view(SpacerView(1))

    def run(self, ctx):
        while True:
            path = self.input_view()

            if path is None:
                return False

            logger.debug(f'FilePatternStep pattern is "{path}"')

            # remove display aliases

            inv = {alias: entity for entity, alias in self.entity_display_aliases.items()}

            i = 0
            _path = ""
            for match in tag_parse.finditer(path):
                groupdict = match.groupdict()
                if groupdict.get("tag_name") in inv:
                    _path += path[i : match.start("tag_name")]
                    _path += inv[match.group("tag_name")]
                    i = match.end("tag_name")

            _path += path[i:]
            path = _path

            # create file obj

            try:
                filedict = {**self.filedict, "path": path, "tags": {}}
                _, ext = split_ext(path)
                filedict["extension"] = self._transform_extension(ext)

                loadresult = self.schema().load(filedict)
                assert isinstance(loadresult, File), "Invalid schema load result"
                self.fileobj = loadresult

                return True
            except Exception as e:
                logger.exception("Exception: %s", e)

                error_color = self.app.layout.color.red
                self.input_view.show_message(TextElement(str(e), color=error_color))

                if ctx.debug:
                    raise

    def next(self, ctx):
        ctx.spec.files.append(self.fileobj)

        return AskForMissingEntities(
            self.app,
            {**self.entity_display_aliases},
            [*self.ask_if_missing_entities],
            self.suggest_file_stem,
            self.next_step_type,
        )(ctx)
