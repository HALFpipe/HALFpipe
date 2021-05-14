# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Dict

from pathlib import Path
from os.path import relpath
from shutil import rmtree
import json
from collections import OrderedDict

from inflection import camelize

from calamities.pattern.glob import _rlistdir
from ...model.file import FileSchema
from ...model.tags import entity_longnames, entities
from ...model.utils import get_nested_schema_field_names
from ...utils import formatlikebids, splitext
from ..metadata import canonicalize_direction_code

from bids.layout import Config
from bids.layout.writing import build_path
import bids.config

bids.config.set_option("extension_initial_dot", True)
bidsconfig = Config.load("bids")

bidsversion = "1.4.0"


class BidsDatabase:
    def __init__(self, database):
        self.database = database

        # indexed by bids_path

        self.file_paths: Dict[str, str] = dict()
        self._tags: Dict[str, Dict] = dict()
        self._metadata: Dict[str, Dict] = dict()

        # indexed by file_path

        self.bids_paths: Dict[str, str] = dict()

    def put(self, file_path: str) -> str:
        bids_path = self.bids_paths.get(file_path)

        if bids_path is not None:
            return bids_path  # already added

        tags = self.database.tags(file_path)

        _tags = dict()
        for k, v in tags.items():
            bidsentity = k
            if bidsentity in entity_longnames:
                bidsentity = entity_longnames[bidsentity]

            if k in entities:
                _tags[bidsentity] = formatlikebids(v)
            else:
                if k == "suffix" and tags.get("datatype") == "fmap":
                    k = "fmap"
                _tags[k] = v

        bids_path = str(
            build_path(_tags, bidsconfig.default_path_patterns)
        )

        self.bids_paths[file_path] = str(bids_path)

        self.file_paths[bids_path] = str(file_path)

        self._tags[bids_path] = _tags

        # traverse schemas to find subclass

        schema = FileSchema
        while hasattr(schema, "type_field") and hasattr(schema, "type_schemas"):
            v = self.database.tagval(file_path, schema.type_field)
            schema = schema.type_schemas[v]

        instance = schema()

        metadata = OrderedDict()
        if "metadata" in instance.fields:
            # manual conversion

            if self.database.tagval(file_path, "datatype") == "func":
                task = self.database.tagval(file_path, "task")
                if task is not None:
                    metadata["TaskName"] = task

            # automated conversion

            metadata_keys = get_nested_schema_field_names(instance, "metadata")
            for key in metadata_keys:
                self.database.fillmetadata(key, [file_path])
                value = self.database.metadata(file_path, key)

                if value is not None:

                    # transform metadata

                    if key.endswith("direction"):
                        value = canonicalize_direction_code(value, file_path)

                    if key == "slice_timing_code":
                        if not self.database.fillmetadata("slice_timing", [file_path]):
                            continue

                        key = "slice_timing"
                        value = self.database.metadata(file_path, key)

                    bids_key = camelize(key)

                    # add to sidecar
                    metadata[bids_key] = value

        self._metadata[bids_path] = metadata

        return bids_path

    def tobids(self, file_path):
        return self.bids_paths.get(file_path)

    def frombids(self, bids_path):
        return self.file_paths.get(bids_path)

    def tags(self, bids_path):
        """
        get a dictionary of entity -> value for a specific bids_path
        """
        return self._tags.get(bids_path)

    def tagval(self, bids_path, entity):

        if isinstance(bids_path, (list, tuple)):  # vectorize
            return [self.tagval(fp, entity) for fp in bids_path]

        tagdict = self._tags.get(bids_path)

        if tagdict is not None:
            return tagdict.get(entity)

    def write(self, bidsdir):
        bidsdir = Path(bidsdir)
        if bidsdir.is_symlink():
            raise ValueError("Will not write to symlink")
        bidsdir.mkdir(parents=True, exist_ok=True)

        bids_paths = set()

        dataset_description_path = bidsdir / "dataset_description.json"
        bids_paths.add(dataset_description_path)

        dataset_description = {
            "Name": self.database.sha1,
            "BIDSVersion": bidsversion,
            "DatasetType": "raw",
        }

        with open(dataset_description_path, "w") as f:
            json.dump(dataset_description, f, indent=4)

        # image files

        for bids_path, file_path in self.file_paths.items():
            bids_path = Path(bidsdir) / bids_path
            bids_paths.add(bids_path)
            bids_path.parent.mkdir(parents=True, exist_ok=True)

            if bids_path.is_file():
                continue  # ignore real files
            elif bids_path.is_symlink():
                if bids_path.resolve() == Path(file_path).resolve():
                    continue  # nothing to be done
                else:
                    bids_path.unlink()  # symlink points to different file
            relative_file_path = relpath(file_path, start=bids_path.parent)
            bids_path.symlink_to(relative_file_path)

        # sidecar files

        for bids_path in self.file_paths.keys():
            metadata = self._metadata.get(bids_path)

            if metadata is not None and len(metadata) > 0:
                basename, _ = splitext(bids_path)
                sidecar_path = Path(bidsdir) / Path(bids_path).parent / f"{basename}.json"

                bids_paths.add(sidecar_path)

                jsonstr = json.dumps(metadata, indent=4, sort_keys=False)
                if sidecar_path.is_file():
                    with open(sidecar_path, "r") as f:
                        if jsonstr == f.read():
                            continue

                with open(sidecar_path, "w") as f:
                    f.write(jsonstr)

        # remove unnecessary files

        files_to_keep = set()
        for bids_path in bids_paths:
            relative_bids_path = relpath(bids_path, start=bidsdir)

            # use relative paths to limit parents to bidsdir
            files_to_keep.add(relative_bids_path)
            files_to_keep.update(
                map(str, Path(relative_bids_path).parents)
            )

        for file_path in _rlistdir(bidsdir, False):
            relative_file_path = relpath(file_path, start=bidsdir)
            if relative_file_path not in files_to_keep:
                p = Path(file_path)
                if not p.is_dir():
                    p.unlink()
                else:
                    rmtree(p)
