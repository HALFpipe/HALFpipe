# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from sdcflows.workflows.pepolar import check_pes

from ..ingest.database import Database
from ..ingest.metadata.direction import canonicalize_direction_code
from ..logging import logger
from ..utils.format import inflect_engine as pe


def collect_pe_dir(database: Database, c: str):
    database.fillmetadata("phase_encoding_direction", [c])
    pe_dir = canonicalize_direction_code(
        database.metadata(c, "phase_encoding_direction"),
        c,
    )
    return pe_dir


def collect_fieldmaps(
    database: Database, bold_file_path: str, silent: bool = False
) -> list[str]:
    sub = database.tagval(bold_file_path, "sub")
    filters = dict(sub=sub)  # enforce same subject

    session = database.tagval(bold_file_path, "ses")
    if session is not None:  # enforce fmaps from same session
        filters.update(dict(ses=session))

    candidates = database.associations(bold_file_path, datatype="fmap", **filters)

    if candidates is None:
        return list()

    candidates = set(candidates)

    # filter phase maps
    magnitude_map: dict[str, list[str]] = {
        "phase1": ["magnitude1", "magnitude2"],
        "phase2": ["magnitude1", "magnitude2"],
        "phasediff": ["magnitude1", "magnitude2"],
        "fieldmap": ["magnitude"],
    }

    incomplete = set()
    for c in candidates:
        suffix = database.tagval(c, "suffix")
        assert isinstance(suffix, str)
        if suffix not in magnitude_map:
            continue
        magnitude: list[str] = magnitude_map[suffix]

        has_magnitude = any(
            database.tagval(c, "suffix") in magnitude for c in candidates
        )
        if not has_magnitude:
            incomplete.add(c)

    if len(incomplete) > 0:
        if silent is not True:
            incomplete_str = pe.join(sorted(incomplete))
            logger.info(
                f"Skipping field maps {incomplete_str} due to missing magnitude images"
            )
        candidates -= incomplete

    # filter pepolar
    epi_fmaps = list()
    for c in candidates:
        suffix = database.tagval(c, "suffix")
        assert isinstance(suffix, str)
        if suffix != "epi":
            continue

        epi_fmaps.append((c, collect_pe_dir(database, c)))

    if len(epi_fmaps) > 0:
        try:
            check_pes(epi_fmaps, collect_pe_dir(database, bold_file_path))
        except ValueError:
            incomplete = set(c for c, _ in epi_fmaps)
            if silent is not True:
                incomplete_str = pe.join(sorted(incomplete))
                logger.info(
                    f"Skipping field maps {incomplete_str} because they do not have matched phase encoding directions"
                )
            candidates -= incomplete

    return sorted(candidates)
