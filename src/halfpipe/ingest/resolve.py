# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from itertools import product
from os.path import basename
from pathlib import Path
from pprint import pformat
from typing import Any, Generator

import marshmallow.exceptions
from bids import BIDSLayout
from bids.layout.index import BIDSLayoutIndexer
from bids.layout.models import BIDSFile
from marshmallow import EXCLUDE

from ..logging import logger
from ..model.file.base import File
from ..model.file.schema import FileSchema
from ..model.spec import Spec
from ..model.tags import entities, entity_longnames
from ..utils.path import exists, split_ext
from .glob import get_entities_in_path, tag_glob, tag_parse
from .metadata.sidecar import SidecarMetadataLoader

file_schema = FileSchema()
entity_shortnames = {v: k for k, v in entity_longnames.items()}


def to_fileobj(obj: BIDSFile, basemetadata: dict) -> File | None:
    entitydict: dict = obj.get_entities()

    datatype: str | None = entitydict.get("datatype")
    suffix: str | None = entitydict.get("suffix")
    extension: str | None = entitydict.get("extension")

    if datatype is None:
        return None  # exclude README and dataset_description.json etc

    if extension is not None:
        if not extension.startswith("."):
            extension = f".{extension}"

    if not isinstance(obj.path, str):
        return None  # need path
    if not exists(obj.path):
        return None  # should exist

    path: str = obj.path

    metadata: dict = dict(**basemetadata)
    metadata.update(obj.get_metadata())

    tags: dict = dict()
    for k, v in entitydict.items():
        entity = entity_shortnames[k] if k in entity_shortnames else k
        if entity in entities:
            tags[entity] = str(v)

    filedict: dict[str, Any] = dict(
        datatype=datatype,
        suffix=suffix,
        extension=extension,
        path=path,
        tags=tags,
        metadata=metadata,
    )

    try:
        fileobj = file_schema.load(filedict, unknown=EXCLUDE)
        if isinstance(fileobj, File):
            return fileobj
    except marshmallow.exceptions.ValidationError as e:
        log_method = logger.warning

        if extension == ".json":
            log_method = logger.debug  # silence
        elif datatype == "dwi":
            log_method = logger.debug  # silence
        elif datatype == "anat":
            log_method = logger.info  # T2w and FLAIR
        elif basename(path).startswith("."):  # is hidden
            log_method = logger.debug  # silence

        log_method(
            f'Skipping unsupported file "{path}" because %s',
            e,
            exc_info=False,
            stack_info=False,
        )

    return None


class ResolvedSpec:
    def __init__(self, spec: Spec, bids_database_dir: Path | None = None) -> None:
        self.spec = spec
        self.bids_database_dir = bids_database_dir

        self.fileobj_by_filepaths: dict[str, File] = dict()

        self.specfileobj_by_filepaths: dict[str, File] = dict()
        self.fileobjs_by_specfilepaths: dict[str, list[File]] = dict()

        for fileobj in self.spec.files:
            self.resolve(fileobj)

    @property
    def resolved_files(self) -> Generator[File, None, None]:
        yield from self.fileobj_by_filepaths.values()

    def put(self, fileobj: File) -> list[File]:
        self.spec.put(fileobj)
        return self.resolve(fileobj)

    def _resolve_fileobj_with_tags(self, fileobj: File) -> list[File]:
        tagglobres = list(tag_glob(fileobj.path))
        if len(tagglobres) == 0:
            logger.warning(f'No files found for query "{fileobj.path}"')

        tmplstr = tag_parse.sub("{\\g<tag_name>}", fileobj.path)  # remove regex information from path if present

        resolved_files: list[File] = list()

        for filepath, tagdict in tagglobres:
            assert isinstance(tagdict, dict)

            filedict = file_schema.dump(fileobj)
            assert isinstance(filedict, dict)

            filedict["path"] = filepath
            _, filedict["extension"] = split_ext(filepath)

            tagdict.update(filedict.get("tags", dict()))

            filedict["tags"] = tagdict
            logger.debug(f"ResolvedSpec._resolve_fileobj_with_tags-> tagdict:{tagdict}")

            filedict["tmplstr"] = tmplstr

            logger.debug(f'Resolved "{pformat(filedict)}" from "{pformat(file_schema.dump(fileobj))}"')

            resolved_fileobj = file_schema.load(filedict)
            assert isinstance(resolved_fileobj, File)

            self.fileobj_by_filepaths[filepath] = resolved_fileobj
            self.specfileobj_by_filepaths[resolved_fileobj.path] = fileobj

            resolved_files.append(resolved_fileobj)

        return resolved_files

    def _resolve_bids(self, fileobj: File) -> list[File]:
        logger.info("BIDS resolve started for path=%s", fileobj.path)

        if not exists(fileobj.path):
            logger.warning(
                'Skipping BIDS directory "%s" (missing or insufficient permissions)',
                fileobj.path,
            )
            return []

        # ---- BIDS layout -----------------------------------------------------
        validate = False
        reset_database = self.bids_database_dir is None

        logger.debug(
            "Initializing BIDSLayout (validate=%s, reset_database=%s, database_path=%s)",
            validate,
            reset_database,
            self.bids_database_dir,
        )

        layout = BIDSLayout(
            root=fileobj.path,
            reset_database=reset_database,
            database_path=self.bids_database_dir,
            validate=validate,
            indexer=BIDSLayoutIndexer(
                validate=validate,
                index_metadata=False,
            ),
        )

        # ---- Base metadata ---------------------------------------------------
        basemetadata = {}
        if isinstance(getattr(fileobj, "metadata", None), dict):
            basemetadata.update(fileobj.metadata)

        logger.debug("Base metadata loaded: %s", basemetadata)

        # ---- Resolve files ---------------------------------------------------
        resolved_files: list[File] = []
        layout_files = list(layout.get_files().values())

        logger.info("Found %d files in BIDS layout", len(layout_files))

        for idx, obj in enumerate(layout_files, start=1):
            logger.debug("Processing layout file %d/%d: %s", idx, len(layout_files), obj)

            file = to_fileobj(obj, basemetadata)
            if file is None:
                logger.debug("→ Skipped (to_fileobj returned None)")
                continue

            self.fileobj_by_filepaths[file.path] = file
            self.specfileobj_by_filepaths[file.path] = file
            resolved_files.append(file)

            logger.debug(
                "→ Added file: path=%s datatype=%s tags=%s",
                file.path,
                file.datatype,
                file.tags,
            )

        logger.info("Resolved %d files total", len(resolved_files))

        # ---- IntendedFor extraction -----------------------------------------
        # intended_for: dict[str, frozenset[tuple[str, str]]] = {}
        intended_for: dict[str, list[frozenset[tuple[str, str]]]] = defaultdict(list)

        for idx, file in enumerate(resolved_files, start=1):
            if file.datatype != "fmap":
                continue

            logger.debug("Reading IntendedFor metadata (%d): %s", idx, file.path)

            metadata = SidecarMetadataLoader.load(file.path)
            if not metadata:
                logger.debug("→ No sidecar metadata found")
                continue

            intended_for_paths = metadata.get("intended_for")
            if not intended_for_paths:
                logger.debug("→ No IntendedFor field present")
                continue

            fmap_tags = frozenset(file.tags.items())
            logger.debug(
                "→ fmap tags=%s intended_for=%s",
                fmap_tags,
                intended_for_paths,
            )

            for path in intended_for_paths:
                # intended_for[path] = fmap_tags
                # MODIFIED: append instead of overwrite (preserve AP + PA)
                intended_for[path].append(fmap_tags)

        logger.info(
            "Collected IntendedFor mappings for %d target paths",
            len(intended_for),
        )

        # ---- Match IntendedFor → files --------------------------------------
        informed_by: dict[frozenset[tuple[str, str]], list[frozenset[tuple[str, str]]]] = defaultdict(list)

        for file in resolved_files:
            file_tags = frozenset(file.tags.items())

            for target_path, fmap_tags_list in intended_for.items():
                if file.path.endswith(target_path):
                    for fmap_tags in fmap_tags_list:
                        # MODIFIED: handle multiple fmap tags per path
                        informed_by[file_tags].append(fmap_tags)
                        logger.debug(
                            "Matched IntendedFor: file=%s ← fmap_tags=%s",
                            file.path,
                            fmap_tags,
                        )

        logger.info(
            "Matched %d files to fmap IntendedFor rules",
            len(informed_by),
        )

        # ---- Build entity mappings ------------------------------------------
        mappings: set[tuple[tuple[str, str], tuple[str, str]]] = set()

        for func_tags, fmap_tags_list in informed_by.items():
            for fmap_tags in fmap_tags_list:
                for func_tag, fmap_tag in product(func_tags, fmap_tags):
                    if "sub" in (func_tag[0], fmap_tag[0]):
                        continue
                    if func_tag[0] == fmap_tag[0]:
                        continue

                    mappings.add((func_tag, fmap_tag))

        logger.debug("Derived %d entity mappings", len(mappings))

        # ---- Build IntendedFor rules ----------------------------------------
        intended_for_rules = defaultdict(list)

        for func_tag, fmap_tag in mappings:
            func_entity, func_val = func_tag
            fmap_entity, fmap_val = fmap_tag

            intended_for_rules[f"{fmap_entity}.{fmap_val}"].append(f"{func_entity}.{func_val}")

        if intended_for_rules:
            logger.info(
                "Inferred fmap → func IntendedFor rules:\n%s",
                pformat(dict(intended_for_rules)),
            )

            for file in resolved_files:
                if file.datatype == "fmap":
                    file.intended_for = intended_for_rules

        logger.info("BIDS resolve completed successfully")
        return resolved_files

    def resolve(self, fileobj: File) -> list[File]:
        logger.debug(f"ResolvedSpec->resolve: {fileobj.path}")
        if len(get_entities_in_path(fileobj.path)) == 0:
            if fileobj.datatype == "bids":
                logger.debug("ResolvedSpec->resolve: len==0 ->bids")
                resolved_files = self._resolve_bids(fileobj)
            else:
                logger.debug("ResolvedSpec->resolve: len==0 -> else")
                resolved_files = [fileobj]
                self.fileobj_by_filepaths[fileobj.path] = fileobj
        else:
            logger.debug("ResolvedSpec->resolve: _resolve_fileobj_with_tags")

            resolved_files = self._resolve_fileobj_with_tags(fileobj)

        self.fileobjs_by_specfilepaths[fileobj.path] = resolved_files
        logger.debug(f"ResolvedSpec->resolve: {fileobj.__dict__}")

        return resolved_files

    def fileobj(self, filepath: str) -> File | None:
        return self.fileobj_by_filepaths.get(filepath)

    def specfileobj(self, filepath: str) -> File | None:
        return self.specfileobj_by_filepaths.get(filepath)

    def fromspecfileobj(self, specfileobj: File) -> list[File] | None:
        return self.fileobjs_by_specfilepaths.get(specfileobj.path)
