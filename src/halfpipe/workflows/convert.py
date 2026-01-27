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
    for bold_path, associated_paths in bold_paths_dict.items():
        try:
            bold_bids_path = Path(bids_database.put(bold_path))
        except ValueError as e:
            logger.warning(f'Skipping "{bold_path}" due to error "{e}"', exc_info=e)
            continue

        parts = list(bold_bids_path.parts)
        # remove path prefixes until we hit subject dir
        while True:
            part = parts.pop(0)

            if part.startswith("sub-"):
                break

        rel_bold_bids_path = str(Path(*parts))

        for path in associated_paths:
            try:
                bids_path = bids_database.put(path)
            except ValueError as e:
                logger.warning(f'Skipping "{path}" due to {e}', exc_info=e)
                continue

            if database.tagval(path, "datatype") != "fmap":
                continue
            if database.tagval(path, "suffix") in ["magnitude1", "magnitude2"]:
                continue

            metadata = bids_database._metadata[bids_path]
            if "IntendedFor" not in metadata:
                metadata["IntendedFor"] = list()

            metadata["IntendedFor"].append(rel_bold_bids_path)
