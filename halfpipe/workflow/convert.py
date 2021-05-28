# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import List, Dict

from pathlib import Path
from operator import attrgetter

from ..io.index import Database, BidsDatabase
from ..utils import logger


def convert_all(
        database: Database,
        bids_database: BidsDatabase,
        bold_file_paths_dict: Dict[str, List[str]]
):
    for bold_file_path, associated_file_paths in bold_file_paths_dict.items():

        try:
            bold_bids_path = bids_database.put(bold_file_path)
        except ValueError as e:
            logger.warning(f'Cannot convert "{bold_file_path}" to BIDS, skipping', exc_info=e)
            continue

        bold_bids_path_obj = Path(bold_bids_path)
        bold_bids_path_parents = list(
            map(attrgetter("name"), bold_bids_path_obj.parents)
        )
        # remove path prefixes until we hit subject dir
        while not bold_bids_path_parents[-1].startswith("sub-"):
            bold_bids_path_parents.pop(-1)

        relative_bold_bids_path = str(Path(
            *bold_bids_path_parents,
            bold_bids_path_obj.name
        ))

        for file_path in associated_file_paths:

            try:
                bids_path = bids_database.put(file_path)
            except ValueError as e:
                logger.warning(f'Cannot convert "{file_path}" to BIDS, skipping', exc_info=e)
                continue

            if database.tagval(file_path, "datatype") != "fmap":
                continue
            if database.tagval(file_path, "suffix") in ["magnitude1", "magnitude2"]:
                continue

            metadata = bids_database._metadata[bids_path]
            if "IntendedFor" not in metadata:
                metadata["IntendedFor"] = list()

            metadata["IntendedFor"].append(relative_bold_bids_path)
