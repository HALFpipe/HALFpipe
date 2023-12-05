# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from sdcflows.workflows.pepolar import check_pes

from ..ingest.database import Database
from ..ingest.metadata.direction import canonicalize_direction_code
from ..logging import logger
from ..utils.format import inflect_engine as pe


def collect_pe_dir(database: Database, c: str):
    """
    Collects and canonicalizes the phase encoding direction for a given file.

    The function fills the metadata for the specified file with the phase encoding
    direction information and then retrieves and canonicalizes the phase encoding
    direction using the `canonicalize_direction_code` function. The function assumes
    that the specified file contains the necessary metadata field and relies on the
    `canonicalize_direction_code` function to handle variations in encoding
    direction codes.

    Parameters
    ----------
    database : Database
        The database containing information about the dataset.
    c : str
        The file path or identifier for which the phase encoding direction is
        collected.

    Returns
    -------
    str
        The canonicalized phase encoding direction for the specified file.
    """
    database.fillmetadata("phase_encoding_direction", [c])
    pe_dir = canonicalize_direction_code(
        database.metadata(c, "phase_encoding_direction"),
        c,
    )
    return pe_dir


def collect_fieldmaps(
    database: Database, bold_file_path: str, silent: bool = False
) -> list[str]:
    """
    Collects and filters field map files associated with a given functional source file.

    The function identifies and filters field map files associated with the specified
    functional source file in the provided database. It filters based on subject,
    datatype ('fmap'), and, if applicable, the session. The function further filters
    out incomplete field maps and pepolar images, logging relevant information.

    The function uses metadata from the provided database to filter and select
    field maps. It logs information about skipped field maps and pepolar images based
    on completeness and matching phase encoding directions. The returned list is sorted
    for consistency.

    Parameters
    ----------
    database : Database
        The database containing information about the dataset.
    bold_file_path : str
        The path to the functional source file for which field maps are collected.
    silent : bool, optional
        If True, suppresses logging of information about skipped field maps.

    Returns
    -------
    list[str]
        A list of paths to the collected and filtered field map files associated with
        the specified functional source file. The list is sorted for consistency.

    """
    bold_file_tags = database.tags(bold_file_path)
    if bold_file_tags is None:
        return list()
    bold_file_tags = bold_file_tags.copy()  # Ensure modification has no side effects

    sub = bold_file_tags.get("sub")
    if sub is None:
        return list()
    # Ensure same subject and datatype
    filters: dict[str, str] = dict(sub=sub, datatype="fmap")
    # If applicable, ensure fmaps from same session
    session = bold_file_tags.get("ses")
    if session is not None:
        filters.update(dict(ses=session))
    # Do not filter by `dir` tag, because we might miss compatible field maps otherwise
    if "dir" in bold_file_tags:
        del bold_file_tags["dir"]

    matching_files = database.associations2(bold_file_tags, filters)
    if matching_files is None:
        return list()
    candidates: set[str] = set(matching_files)

    if candidates is None:
        return list()

    candidates = set(candidates)

    # Filter phase maps
    magnitude_map: dict[str, list[str]] = {
        "phase1": ["magnitude1", "magnitude2"],
        "phase2": ["magnitude1", "magnitude2"],
        "phasediff": ["magnitude1", "magnitude2"],
        "fieldmap": ["magnitude"],
    }

    incomplete: set[str] = set()
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

    # Filter pepolar
    epi_fmaps = list()
    for c in candidates:
        suffix = database.tagval(c, "suffix")
        if not isinstance(suffix, str):
            continue
        if suffix != "epi":
            continue

        epi_fmaps.append((c, collect_pe_dir(database, c)))

    if len(epi_fmaps) > 0:
        try:
            check_pes(epi_fmaps, collect_pe_dir(database, bold_file_path))
        except ValueError:
            if silent is not True:
                incomplete_str = pe.join(
                    sorted(f'"{c}" with direction {dir}' for c, dir in epi_fmaps)
                )
                logger.info(
                    f"Skipping field maps {incomplete_str} because they do not have matched phase encoding directions"
                )
            candidates -= set(c for c, _ in epi_fmaps)

    return sorted(candidates)
