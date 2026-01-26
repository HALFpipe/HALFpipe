# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from ..ingest.bids import BidsDatabase
from ..ingest.database import Database
from ..logging import logger


def convert_all(
    database: Database,
    bids_database: BidsDatabase,
    bold_paths_dict: dict[str, list[str]],
):
    """
    Convert all BOLD files and their associated fmap files to BIDS paths,
    and update IntendedFor metadata.

    Parameters
    ----------
    database : Database
        The halfpipe database containing file tag info.
    bids_database : BidsDatabase
        The BIDS database to write paths and metadata into.
    bold_paths_dict : dict[str, list[str]]
        Mapping from BOLD file paths to associated fmap paths.
    """
    for bold_path, associated_paths in bold_paths_dict.items():
        logger.debug(f"Processing BOLD file: {bold_path} with associated fmap files: {associated_paths}")

        # ---- Put bold file in BIDS ----
        try:
            bold_bids_path = Path(bids_database.put(bold_path))
            logger.debug(f"BOLD file mapped to BIDS path: {bold_bids_path}")
        except ValueError as e:
            logger.warning(f'Skipping "{bold_path}" due to error "{e}"', exc_info=False)
            continue

        # ---- Make relative path starting from subject dir ----
        parts = list(bold_bids_path.parts)
        while True:
            part = parts.pop(0)
            if part.startswith("sub-"):
                break
        rel_bold_bids_path = str(Path(*parts))
        logger.debug(f"Relative BIDS path for IntendedFor: {rel_bold_bids_path}")

        # ---- Process associated fmap files ----
        for path in associated_paths:
            try:
                fmap_bids_path = bids_database.put(path)
                logger.debug(f'Fmap file "{path}" mapped to BIDS path: {fmap_bids_path}')
            except ValueError as e:
                logger.warning(f'Skipping "{path}" due to error "{e}"', exc_info=False)
                continue

            # ---- Skip if not fmap or if magnitude images ----
            datatype = database.tagval(path, "datatype")
            suffix = database.tagval(path, "suffix")
            if datatype != "fmap":
                logger.debug(f'Skipping "{path}" because datatype={datatype} is not fmap')
                continue
            if suffix in ["magnitude1", "magnitude2"]:
                logger.debug(f'Skipping "{path}" because suffix={suffix} is magnitude')
                continue

            # ---- Update IntendedFor ----
            metadata = bids_database._metadata[fmap_bids_path]
            if "IntendedFor" not in metadata:
                metadata["IntendedFor"] = []
                logger.debug(f'Initialized IntendedFor list for "{fmap_bids_path}"')

            if rel_bold_bids_path not in metadata["IntendedFor"]:
                metadata["IntendedFor"].append(rel_bold_bids_path)
                logger.debug(f'Added "{rel_bold_bids_path}" to IntendedFor of "{fmap_bids_path}"')
