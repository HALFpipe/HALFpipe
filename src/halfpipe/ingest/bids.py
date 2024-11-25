# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from os.path import relpath
from pathlib import Path
from shutil import rmtree
from typing import Any, overload

from bids.layout import Config
from bids.layout.writing import build_path
from inflection import camelize

from ..collect.metadata import collect_metadata
from ..logging import logger
from ..model.tags import entities, entity_longnames
from ..utils.format import format_like_bids
from ..utils.hash import int_digest
from ..utils.path import rlistdir, split_ext
from .database import Database

bids_config = Config.load("bids")
bids_version = "1.4.0"


def get_bids_metadata(database: Database, file_path: str | Path) -> dict[str, Any]:
    metadata = collect_metadata(database, file_path)

    return {camelize(key): value for key, value in metadata.items()}


class BidsDatabase:
    def __init__(self, database: Database) -> None:
        self.database = database

        # indexed by bids_path

        self.file_paths: dict[str, str] = dict()
        self.bids_tags: dict[str, dict] = dict()
        self._metadata: dict[str, dict] = dict()

        # indexed by file_path

        self.bids_paths: dict[str, str] = dict()

    def put(self, file_path: str) -> str:
        bids_path = self.bids_paths.get(file_path)

        if bids_path is not None:
            return bids_path  # already added

        tags = self.database.tags(file_path)
        if not isinstance(tags, dict):
            raise ValueError(f'File "{file_path}" has no tags')

        bids_tags = dict()
        for entity, value in tags.items():
            bids_entity = entity

            if bids_entity in entity_longnames:  # map to long names
                bids_entity = entity_longnames[bids_entity]

            if bids_entity == "task" and tags.get("datatype") == "fmap":
                assert "acq" not in tags
                bids_entity = "acquisition"

            if bids_entity == "run":
                if not value.isdecimal():  # enforce run to be numerical
                    run_identifier = str(int_digest(value))[:4]
                    logger.warning(f'Converting run identifier "{value}" to number "{run_identifier}" for BIDS-compliance')
                    value = run_identifier

            if entity in entities:
                bids_tags[bids_entity] = format_like_bids(value)
            else:
                bids_tags[entity] = value

        bids_path_result = build_path(bids_tags, bids_config.default_path_patterns)

        if bids_path_result is None:
            raise ValueError(f'Unable to build BIDS-compliant path for "{file_path}" with tags "{bids_tags}"')

        bids_path = str(bids_path_result)

        if bids_path in self.file_paths:
            if self.file_paths[bids_path] != str(file_path):
                raise ValueError("Cannot assign different files to the same BIDS path")

        self.bids_paths[file_path] = str(bids_path)
        self.file_paths[bids_path] = str(file_path)

        self.bids_tags[bids_path] = bids_tags

        self._metadata[bids_path] = get_bids_metadata(self.database, file_path)

        return bids_path

    def to_bids(self, file_path: str) -> str | None:
        return self.bids_paths.get(file_path)

    def from_bids(self, bids_path: str) -> str | None:
        return self.file_paths.get(bids_path)

    def tags(self, bids_path: str) -> dict | None:
        """
        get a dictionary of entity -> value for a specific bids_path
        """
        return self.bids_tags.get(bids_path)

    @overload
    def get_tag_value(self, bids_path: list[str], entity: str) -> list: ...

    @overload
    def get_tag_value(self, bids_path: str, entity: str) -> str | None: ...

    def get_tag_value(self, bids_path: list[str] | str, entity: str) -> str | list | None:
        if isinstance(bids_path, (list, tuple)):  # vectorize
            return [self.get_tag_value(b, entity) for b in bids_path]

        tagdict = self.tags(bids_path)
        if tagdict is not None:
            return tagdict.get(entity)

        return None

    def write(self, bidsdir: str | Path):
        bidsdir = Path(bidsdir)
        if bidsdir.is_symlink():
            raise ValueError("Will not write to symlink")
        bidsdir.mkdir(parents=True, exist_ok=True)

        bids_paths = set()

        dataset_description_path = bidsdir / "dataset_description.json"
        bids_paths.add(dataset_description_path)

        dataset_description = {
            "Name": self.database.sha1,
            "BIDSVersion": bids_version,
            "DatasetType": "raw",
        }

        with open(dataset_description_path, "w") as f:
            json.dump(dataset_description, f, indent=4)

        # image files
        for bids_path_str, file_path in self.file_paths.items():
            if bids_path_str is None:
                raise ValueError(f'File "{file_path}" has no BIDS path')
            bids_path = Path(bidsdir) / bids_path_str
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
        for bids_path_str in self.file_paths.keys():
            metadata = self._metadata.get(bids_path_str)

            if metadata is not None and len(metadata) > 0:
                bids_path = Path(bids_path_str)
                basename, _ = split_ext(bids_path)
                sidecar_path = Path(bidsdir) / bids_path.parent / f"{basename}.json"

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
            files_to_keep.update(map(str, Path(relative_bids_path).parents))

        for file_path in rlistdir(bidsdir):
            relative_file_path = relpath(file_path, start=bidsdir)
            if relative_file_path not in files_to_keep:
                p = Path(file_path)
                if not p.is_dir():
                    p.unlink()
                else:
                    rmtree(p)
