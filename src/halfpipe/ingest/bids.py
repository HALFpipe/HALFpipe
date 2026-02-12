# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import re
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


def replace_t1w_with_mask(filename: str) -> str:
    """
    Replaces the '_T1w.nii.gz' suffix with '_mask.nii.gz' in the given filename.

    Parameters:
        filename (str): Input filename expected to end with '_T1w.nii.gz'.

    Returns:
        str: Modified filename with '_mask.nii.gz' suffix.

    Raises:
        ValueError: If the input string does not end with '_T1w.nii.gz'.
    """
    if not filename.endswith("_T1w.nii.gz"):
        raise ValueError("Input must end with '_T1w.nii.gz'")

    return re.sub(r"_T1w\.nii\.gz$", "_roi.nii.gz", filename)


class BidsDatabase:
    def __init__(self, database: Database) -> None:
        logger.info("BidsDatabase initialization started")

        self.database = database

        # indexed by bids_path

        self.file_paths: dict[str, str] = dict()
        self.bids_tags: dict[str, dict] = dict()
        self._metadata: dict[str, dict] = dict()

        # indexed by file_path

        self.bids_paths: dict[str, str] = dict()

        logger.info("BidsDatabase initialization completed")

    def put(self, file_path: str) -> str:
        logger.debug("BidsDatabase.put-> start file_path=%s", file_path)

        bids_path = self.bids_paths.get(file_path)

        if bids_path is not None:
            logger.debug(
                "BidsDatabase.put-> already exists: %s → %s",
                file_path,
                bids_path,
            )
            return bids_path  # already added

        tags = self.database.tags(file_path)
        if not isinstance(tags, dict):
            raise ValueError(
                f'BidsDatabase.put-> file has no tags: "{file_path}"'
            )

        logger.debug(
            "BidsDatabase.put-> source tags=%s",
            tags,
        )

        bids_tags = dict()
        for entity, value in tags.items():
            bids_entity = entity

            if bids_entity in entity_longnames:  # map to long names
                bids_entity = entity_longnames[bids_entity]
                logger.debug(
                    "BidsDatabase.put-> mapped entity %s → %s",
                    entity,
                    bids_entity,
                )

            if bids_entity == "task" and tags.get("datatype") == "fmap":
                logger.debug(
                    "BidsDatabase.put-> fmap task remapped to acquisition",
                )
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

        logger.debug(
            "BidsDatabase.put-> bids_tags=%s",
            bids_tags,
        )

        # In case of lesion mask presence, we temporary change the suffix to standard anat T1w and let the
        # halfpipe create symbolic path for the files as it was a normal anat T1w file. But afterwards,
        # by checking the suffix (if roi or mask), we change the suffix of the symbolic path (bids_path_result) using the
        # function replace_t1w_with_mask. At the end, we get the mask (roi) file to the same anat folder as it is
        # required by current version of fmriprep. In future, when fmriprep is updated, the masks will follow
        # bids standard and will be relocated to derivates directory.
        suffix = bids_tags.get("suffix")

        # Temporarily override suffix if needed
        build_tags = {**bids_tags, "suffix": "T1w"} if suffix in {"mask", "roi"} else bids_tags
        logger.debug(
            "BidsDatabase.put-> temporary suffix override (%s → T1w)",
            suffix,
        )

        # Single build_path call
        bids_path_result = build_path(build_tags, bids_config.default_path_patterns)

        # Post-process in case of masks (rois)
        if suffix in {"mask", "roi"}:
            bids_path_result = replace_t1w_with_mask(bids_path_result)
            logger.debug(
                "BidsDatabase.put-> restored mask/roi suffix in path",
            )

        if bids_path_result is None:
            raise ValueError(
                f'BidsDatabase.put-> Unable to build BIDS-compliant path for '
                f'"{file_path}" with tags "{bids_tags}"'
            )

        bids_path = str(bids_path_result)

        logger.debug(
            "BidsDatabase.put-> resolved BIDS path=%s",
            bids_path,
        )

        if bids_path in self.file_paths:
            if self.file_paths[bids_path] != str(file_path):
                raise ValueError(
                    f"BidsDatabase.put-> path collision: {bids_path} already mapped to "
                    f"{self.file_paths[bids_path]}"
                )

        self.bids_paths[file_path] = str(bids_path)
        self.file_paths[bids_path] = str(file_path)

        self.bids_tags[bids_path] = bids_tags

        self._metadata[bids_path] = get_bids_metadata(self.database, file_path)

        logger.debug(
            "BidsDatabase.put-> metadata keys=%s",
            list(self._metadata[bids_path].keys()),
        )
        logger.debug("BidsDatabase.put-> completed for %s", file_path)

        return bids_path

    def to_bids(self, file_path: str) -> str | None:
        bids_path = self.bids_paths.get(file_path)
        logger.debug(
            "BidsDatabase.to_bids-> %s → %s",
            file_path,
            bids_path,
        )
        return bids_path

    def from_bids(self, bids_path: str) -> str | None:
        file_path = self.file_paths.get(bids_path)
        logger.debug(
            "BidsDatabase.from_bids-> %s → %s",
            bids_path,
            file_path,
        )
        return file_path

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
        logger.info("BidsDatabase.write-> start bidsdir=%s", bidsdir)

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

        logger.debug("BidsDatabase.write-> wrote dataset_description.json")

        # ---- Image files -------------------------------------------------------
        for idx, (bids_path_str, file_path) in enumerate(self.file_paths.items(), start=1):
            logger.debug(
                "BidsDatabase.write-> image %d/%d: %s ← %s",
                idx,
                len(self.file_paths),
                bids_path_str,
                file_path,
            )
            if bids_path_str is None:
                raise ValueError(f'File "{file_path}" has no BIDS path')
            bids_path = Path(bidsdir) / bids_path_str
            bids_paths.add(bids_path)
            bids_path.parent.mkdir(parents=True, exist_ok=True)

            if bids_path.is_file():
                logger.debug("BidsDatabase.write-> file exists, skipping")
                continue  # ignore real files
            elif bids_path.is_symlink():
                if bids_path.resolve() == Path(file_path).resolve():
                    logger.debug("BidsDatabase.write-> correct symlink exists")
                    continue  # nothing to be done
                else:
                    logger.debug("BidsDatabase.write-> removing incorrect symlink")
                    bids_path.unlink()  # symlink points to different file
            relative_file_path = relpath(file_path, start=bids_path.parent)
            bids_path.symlink_to(relative_file_path)

        # ---- Sidecar files -----------------------------------------------------
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
                            logger.debug(
                                "BidsDatabase.write-> sidecar unchanged: %s",
                                sidecar_path,
                            )
                            continue

                with open(sidecar_path, "w") as f:
                    f.write(jsonstr)

                logger.debug(
                    "BidsDatabase.write-> wrote sidecar: %s",
                    sidecar_path,
                )

        # ---- Cleanup -----------------------------------------------------------
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
                logger.debug(
                    "BidsDatabase.write-> removing obsolete path: %s",
                    p,
                )
                if not p.is_dir():
                    p.unlink()
                else:
                    rmtree(p)

    logger.info("BidsDatabase.write-> completed")
