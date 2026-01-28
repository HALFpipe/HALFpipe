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
    logger.info(
        "convert_all-> start (%d bold entries)",
        len(bold_paths_dict),
    )

    for idx, (bold_path, associated_paths) in enumerate(bold_paths_dict.items(), start=1):
        logger.debug(
            "convert_all-> processing bold %d/%d: %s",
            idx,
            len(bold_paths_dict),
            bold_path,
        )
        # ---- Convert BOLD ---------------------------------------------------
        try:
            bold_bids_path = Path(bids_database.put(bold_path))
            logger.debug(
                "convert_all-> bold converted to BIDS path: %s",
                bold_bids_path,
            )
        except ValueError as e:
            logger.warning(f'Skipping "{bold_path}" due to error "{e}"', exc_info=e)
            continue

        # ---- Build relative IntendedFor path --------------------------------
        parts = list(bold_bids_path.parts)
        logger.debug(
            "convert_all-> bold BIDS path parts=%s",
            parts,
        )
        # remove path prefixes until we hit subject dir
        while True:
            part = parts.pop(0)

            if part.startswith("sub-"):
                break

        rel_bold_bids_path = str(Path(*parts))

        logger.debug(
            "convert_all-> relative IntendedFor path=%s",
            rel_bold_bids_path,
        )

        # ---- Process associated files ---------------------------------------
        for jdx, path in enumerate(associated_paths, start=1):
            logger.debug(
                "convert_all-> processing associated file %d/%d: %s",
                jdx,
                len(associated_paths),
                path,
            )
            try:
                bids_path = bids_database.put(path)
                logger.debug(
                    "convert_all-> associated file converted to BIDS path: %s",
                    bids_path,
                )
            except ValueError as e:
                logger.warning(f'Skipping "{path}" due to {e}', exc_info=e)
                continue

            datatype = database.tagval(path, "datatype")
            suffix = database.tagval(path, "suffix")

            logger.debug(
                "convert_all-> associated file tags: datatype=%s suffix=%s",
                datatype,
                suffix,
            )

            if datatype != "fmap":
                logger.debug(
                    "convert_all-> skipping (datatype=%s != fmap)",
                    datatype,
                )
                continue

            if suffix in ["magnitude1", "magnitude2"]:
                logger.debug(
                    "convert_all-> skipping magnitude fmap (suffix=%s)",
                    suffix,
                )
                continue

            # ---- Update IntendedFor ------------------------------------------
            metadata = bids_database._metadata[bids_path]
            if "IntendedFor" not in metadata:
                logger.debug(
                    "convert_all-> creating IntendedFor list for %s",
                    bids_path,
                )
                metadata["IntendedFor"] = list()

            metadata["IntendedFor"].append(rel_bold_bids_path)

            logger.info(
                "convert_all-> added IntendedFor: %s ← %s",
                bids_path,
                rel_bold_bids_path,
            )

    logger.info("convert_all-> completed")
