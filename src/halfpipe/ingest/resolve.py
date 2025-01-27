# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from itertools import product
from os.path import basename
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
    def __init__(self, spec: Spec) -> None:
        self.spec = spec

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

            filedict["tmplstr"] = tmplstr

            logger.debug(f'Resolved "{pformat(filedict)}" from "{pformat(file_schema.dump(fileobj))}"')

            resolved_fileobj = file_schema.load(filedict)
            assert isinstance(resolved_fileobj, File)

            self.fileobj_by_filepaths[filepath] = resolved_fileobj
            self.specfileobj_by_filepaths[resolved_fileobj.path] = fileobj

            resolved_files.append(resolved_fileobj)

        return resolved_files

    def _resolve_bids(self, fileobj: File) -> list[File]:
        if not exists(fileobj.path):
            logger.warning(
                f'Skipping BIDS directory "{fileobj.path}" because it does not exist or we do not have sufficient permissions.'
            )
            return list()

        # load using pybids
        validate = False  # save time
        layout = BIDSLayout(
            root=fileobj.path,
            reset_database=True,  # force reindex in case files have changed
            absolute_paths=True,
            validate=validate,
            indexer=BIDSLayoutIndexer(
                validate=validate,
                index_metadata=False,  # save time
            ),
        )

        # load override metadata
        basemetadata = dict()
        if hasattr(fileobj, "metadata"):
            metadata = getattr(fileobj, "metadata", None)
            if isinstance(metadata, dict):
                basemetadata.update(metadata)

        resolved_files: list[File] = []
        for obj in layout.get_files().values():
            file: File | None = to_fileobj(obj, basemetadata)

            if file is None:
                continue

            self.fileobj_by_filepaths[file.path] = file
            self.specfileobj_by_filepaths[file.path] = file
            resolved_files.append(file)

        intended_for: dict[str, frozenset[tuple[str, str]]] = dict()
        for file in resolved_files:
            if file.datatype != "fmap":
                continue

            metadata = SidecarMetadataLoader.load(file.path)
            if metadata is None:
                continue

            intended_for_paths = metadata.get("intended_for")
            if intended_for_paths is None:
                continue

            linked_fmap_tags = frozenset(file.tags.items())
            for intended_for_path in intended_for_paths:
                intended_for[intended_for_path] = linked_fmap_tags

        informed_by: dict[frozenset[tuple[str, str]], list[frozenset[tuple[str, str]]]] = defaultdict(list)
        for file in resolved_files:
            file_tags = frozenset(file.tags.items())

            for file_path, linked_fmap_tags in intended_for.items():
                if file.path.endswith(file_path):  # slow performance
                    informed_by[file_tags].append(linked_fmap_tags)

        mappings: set[tuple[tuple[str, str], tuple[str, str]]] = set()
        for func_tags, linked_fmap_tags_list in informed_by.items():
            for linked_fmap_tags in linked_fmap_tags_list:
                for func_tag, linked_fmap_tag in product(func_tags, linked_fmap_tags):
                    if func_tag[0] == "sub" or linked_fmap_tag[0] == "sub":
                        continue
                    if func_tag[0] == linked_fmap_tag[0]:  # only map between different entities
                        continue
                    mappings.add((func_tag, linked_fmap_tag))

        intended_for_rules = defaultdict(list)
        for functag, fmaptag in mappings:
            entity, val = functag
            funcstr = f"{entity}.{val}"

            entity, val = fmaptag
            fmapstr = f"{entity}.{val}"

            intended_for_rules[fmapstr].append(funcstr)

        if len(intended_for) > 0:
            logger.info(
                "Inferred mapping between func and fmap files to be %s",
                pformat(intended_for_rules),
            )
            for file in resolved_files:
                if file.datatype != "fmap":
                    continue
                file.intended_for = intended_for_rules

        return resolved_files

    def resolve(self, fileobj: File) -> list[File]:
        if len(get_entities_in_path(fileobj.path)) == 0:
            if fileobj.datatype == "bids":
                resolved_files = self._resolve_bids(fileobj)
            else:
                resolved_files = [fileobj]
                self.fileobj_by_filepaths[fileobj.path] = fileobj
        else:
            resolved_files = self._resolve_fileobj_with_tags(fileobj)

        self.fileobjs_by_specfilepaths[fileobj.path] = resolved_files

        return resolved_files

    def fileobj(self, filepath: str) -> File | None:
        return self.fileobj_by_filepaths.get(filepath)

    def specfileobj(self, filepath: str) -> File | None:
        return self.specfileobj_by_filepaths.get(filepath)

    def fromspecfileobj(self, specfileobj: File) -> list[File] | None:
        return self.fileobjs_by_specfilepaths.get(specfileobj.path)
