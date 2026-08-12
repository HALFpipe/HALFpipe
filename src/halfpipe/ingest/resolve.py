# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from os.path import basename
from pathlib import Path
from pprint import pformat
from typing import Any, Generator

import marshmallow.exceptions
from bids import BIDSLayout
from bids.exceptions import BIDSValidationError
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


def to_fileobj(obj: BIDSFile, base_metadata: dict[str, Any], base_tags: dict[str, str]) -> File | None:
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

    # Sidecar metadata is not merged here: the layout is built with ``index_metadata=False``,
    # so ``obj.get_metadata()`` is always empty. ``SidecarMetadataLoader`` reads it lazily,
    # applying the inheritance principle via ``sidecar_paths_by_filepaths``.
    metadata: dict = dict(**base_metadata)

    tags: dict = base_tags.copy()
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

        self.intended_for_by_filepaths: dict[str, set[str]] = dict()
        self.sidecar_paths_by_filepaths: dict[str, list[Path]] = dict()
        self.sidecar_metadata_loader = SidecarMetadataLoader(self)

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
        logger.debug("BIDS resolve started for path=%s", fileobj.path)

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
        # Images of datatypes halfpipe does not ingest, such as ``dwi``. They are still part
        # of the dataset's field-map bookkeeping, because they can claim a field map through
        # ``B0FieldSource``, which then rules it out for everything else.
        unresolved_paths: list[str] = list()
        layout_files: list[BIDSFile] = list(layout.get_files().values())

        logger.info("Found %d files in BIDS layout", len(layout_files))

        for idx, obj in enumerate(layout_files, start=1):
            logger.debug("Processing layout file %d/%d: %s", idx, len(layout_files), obj)

            file = to_fileobj(obj, basemetadata, fileobj.tags)
            if file is None:
                # Only actual data files. Files without a datatype, such as ``README``, are
                # not part of the field-map bookkeeping and have no sidecars to search for.
                datatype = obj.get_entities().get("datatype")
                if datatype is not None and isinstance(obj.path, str) and not obj.path.endswith(".json"):
                    if exists(obj.path):
                        unresolved_paths.append(obj.path)
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

        logger.debug("Resolved %d files total", len(resolved_files))

        # ---- Sidecars ---------------------------------------
        resolved_paths = [file.path for file in resolved_files]
        image_paths = resolved_paths + unresolved_paths

        for image_path in image_paths:
            file_directory = Path(image_path).parent

            sidecar_paths: list[Path] = list()
            try:
                for sidecar_path in layout.get_nearest(image_path, extension=".json", strict=True, all_=True):
                    sidecar_directory = Path(sidecar_path).parent
                    # Skip unrelated
                    if not file_directory.is_relative_to(sidecar_directory):
                        continue
                    sidecar_paths.append(Path(sidecar_path))
            except BIDSValidationError as exc_info:
                logger.warning(
                    "Skipping sidecar search for %s because of BIDS validation error",
                    image_path,
                    exc_info=exc_info,
                )
                continue

            # Sort by least specific first
            sidecar_paths.sort(key=lambda p: len(p.parts))

            self.sidecar_paths_by_filepaths[image_path] = sidecar_paths

        # ---- Field-map associations -----------------

        b0_field_source_candidate_paths = [file.path for file in resolved_files if file.datatype != "fmap"] + unresolved_paths
        filepaths_by_b0_field_source: dict[str, set[str]] = defaultdict(set)
        for path in b0_field_source_candidate_paths:
            b0_field_sources = self.sidecar_metadata_loader.load(path).get("b0_field_source")
            if not b0_field_sources:
                continue
            for b0_field_source in b0_field_sources:
                filepaths_by_b0_field_source[b0_field_source].add(path)

        for file in resolved_files:
            if file.datatype != "fmap":
                continue

            sidecar = self.sidecar_metadata_loader.load(file.path)
            targets: set[str] = set()

            for identifier in sidecar.get("b0_field_identifier", []):
                targets.update(filepaths_by_b0_field_source.get(identifier, set()))

            if not targets:
                for entry in sidecar.get("intended_for", []):
                    target = entry.removeprefix("bids::").lstrip("/")
                    targets.update(path for path in resolved_paths if path.endswith(target))

            if not targets:
                if sidecar.get("b0_field_identifier") or sidecar.get("intended_for"):
                    logger.warning(
                        "Ignoring the association of field map %s because none of its targets could be resolved",
                        file.path,
                    )
                continue

            self.intended_for_by_filepaths[file.path] = targets
            logger.debug("Field map %s serves %s", file.path, targets)

        logger.debug("Recorded associations for %d field maps", len(self.intended_for_by_filepaths))
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
