# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from typing import Any, List, Dict, Optional

from collections import defaultdict
from itertools import product
from pprint import pformat
from os.path import basename

from marshmallow import EXCLUDE
import marshmallow.exceptions
from calamities.pattern import tag_glob, tag_parse, get_entities_in_path

from ...model.file import FileSchema, File
from ...model.tags import entities, entity_longnames
from ...utils import splitext, logger
from ...io.metadata.sidecar import SidecarMetadataLoader

import bids.config

bids.config.set_option("extension_initial_dot", True)
from bids import BIDSLayout  # noqa: E402
from bids.layout.models import BIDSFile  # noqa: E402
from bids.layout.index import BIDSLayoutIndexer  # noqa: E402

file_schema = FileSchema()
entity_shortnames = {v: k for k, v in entity_longnames.items()}


def to_fileobj(obj: BIDSFile, basemetadata: Dict) -> Optional[File]:
    entitydict: Dict = obj.get_entities()

    datatype: Optional[str] = entitydict.get("datatype")
    suffix: Optional[str] = entitydict.get("suffix")
    extension: Optional[str] = entitydict.get("extension")

    if datatype is None:
        return  # exclude README and dataset_description.json etc

    if extension is not None:
        if not extension.startswith("."):
            extension = f".{extension}"

    path: str = obj.path

    metadata: Dict = dict(**basemetadata)
    metadata.update(obj.get_metadata())

    tags: Dict = dict()
    for k, v in entitydict.items():
        entity = entity_shortnames[k] if k in entity_shortnames else k
        if entity in entities:
            tags[entity] = str(v)

    filedict: Dict[str, Any] = dict(
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
        if datatype == "dwi":
            log_method = logger.debug  # silence
        if datatype == "anat":
            log_method = logger.info  # T2w and FLAIR
        if basename(path).startswith("."):  # is hidden
            log_method = logger.debug  # silence

        log_method(
            f'Ignored validation error for "{path}": %s',
            e,
            exc_info=False,
            stack_info=False,
        )


class ResolvedSpec:
    def __init__(self, spec):
        self.spec = spec

        self.fileobj_by_filepaths = dict()

        self.specfileobj_by_filepaths = dict()
        self.fileobjs_by_specfilepaths = dict()

        for fileobj in self.spec.files:
            self.resolve(fileobj)

    @property
    def resolved_files(self):
        yield from self.fileobj_by_filepaths.values()

    def put(self, fileobj):
        self.spec.put(fileobj)
        return self.resolve(fileobj)

    def _resolve_fileobj_with_tags(self, fileobj):
        tagglobres = list(tag_glob(fileobj.path))
        if len(tagglobres) == 0:
            logger.warning(f'No files found for query "{fileobj.path}"')

        tmplstr = tag_parse.sub(
            "{\\g<tag_name>}", fileobj.path
        )  # remove regex information from path if present

        resolved_files = []

        for filepath, tagdict in tagglobres:
            assert isinstance(tagdict, dict)

            filedict = file_schema.dump(fileobj)
            assert isinstance(filedict, dict)

            filedict["path"] = filepath
            _, filedict["extension"] = splitext(filepath)

            tagdict.update(
                filedict.get("tags", dict())
            )

            filedict["tags"] = tagdict

            filedict["tmplstr"] = tmplstr

            resolved_fileobj = file_schema.load(filedict)
            assert isinstance(resolved_fileobj, File)

            self.fileobj_by_filepaths[filepath] = resolved_fileobj
            self.specfileobj_by_filepaths[resolved_fileobj.path] = fileobj

            resolved_files.append(resolved_fileobj)

        return resolved_files

    def _resolve_bids(self, fileobj: File) -> List[File]:

        # load using pybids
        validate = False   # save time
        layout = BIDSLayout(
            root=fileobj.path,
            reset_database=True,  # force reindex in case files have changed
            absolute_paths=True,
            validate=validate,
            indexer=BIDSLayoutIndexer(
                validate=validate,
                index_metadata=False,  # save time
            )
        )

        # load override metadata
        basemetadata = dict()
        if hasattr(fileobj, "metadata"):
            metadata = getattr(fileobj, "metadata", None)
            if isinstance(metadata, dict):
                basemetadata.update(metadata)

        resolved_files: List[File] = []
        for obj in layout.get_files().values():
            file: Optional[File] = to_fileobj(obj, basemetadata)

            if file is None:
                continue

            self.fileobj_by_filepaths[file.path] = file
            self.specfileobj_by_filepaths[file.path] = file
            resolved_files.append(file)

        intended_for_mapping = dict()
        for file in resolved_files:
            if file.datatype != "fmap":
                continue

            metadata = SidecarMetadataLoader.load(file.path)

            if metadata is None:
                continue

            intended_for_paths = metadata.get("intended_for")

            if intended_for_paths is None:
                continue

            tagset = frozenset(file.tags.items())

            for path in intended_for_paths:
                intended_for_mapping[path] = tagset

        tag_mapping = defaultdict(list)
        for file in resolved_files:
            tagset = frozenset(file.tags.items())

            for path, fmap_tagset in intended_for_mapping.items():
                if not file.path.endswith(path):  # slow performance
                    continue

                tag_mapping[tagset].append(fmap_tagset)

        mappings = set()
        mapping_sets = [
            set(
                (a, b)
                for fmap in fmaplist
                for a, b in product(func, fmap)
                if a[0] != b[0]
                and "sub" not in (a[0], b[0])
            )
            for func, fmaplist in tag_mapping.items()
        ]
        if len(mapping_sets) > 0:
            mappings.update(*mapping_sets)

        intended_for = defaultdict(list)
        for functag, fmaptag in mappings:
            entity, val = functag
            funcstr = f"{entity}.{val}"

            entity, val = fmaptag
            fmapstr = f"{entity}.{val}"

            intended_for[fmapstr].append(funcstr)

        if len(intended_for) > 0:
            logger.info("Inferred mapping between func and fmap files to be %s", pformat(intended_for))
            for file in resolved_files:
                if file.datatype != "fmap":
                    continue
                file.intended_for = intended_for

        return resolved_files

    def resolve(self, fileobj):
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

    def fileobj(self, filepath):
        return self.fileobj_by_filepaths.get(filepath)

    def specfileobj(self, filepath):
        return self.specfileobj_by_filepaths.get(filepath)

    def fromspecfileobj(self, specfileobj):
        return self.fileobjs_by_specfilepaths.get(specfileobj.path)
