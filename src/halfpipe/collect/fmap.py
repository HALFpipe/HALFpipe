# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..ingest.database import Database
from ..ingest.metadata.direction import canonicalize_direction_code
from ..logging import logger
from ..utils.format import inflect_engine as pe


def _pe_axis_sign(pe: str) -> tuple[str, str]:
    """
    Return (axis, sign) where sign is '+' or '-'.
    Treat 'j' as 'j+' (BIDS allows 'j' with no minus).
    """
    if not pe:
        raise ValueError("Empty PhaseEncodingDirection")
    axis = pe[0]
    sign = '-' if pe.endswith('-') else '+'
    return axis, sign


def has_opposing_pe(epi_fmaps, bold_pe_dir: str) -> bool:
    bold_axis, bold_sign = _pe_axis_sign(bold_pe_dir)

    any_same_axis = False
    any_opposed = False

    for _, fmap_pe in epi_fmaps:
        fmap_axis, fmap_sign = _pe_axis_sign(fmap_pe)

        if fmap_axis != bold_axis:
            continue  # wrong axis, unusable for topup-style pairing

        any_same_axis = True
        if fmap_sign != bold_sign:
            any_opposed = True

    if not any_same_axis:
        raise ValueError(
            "None of the discovered fieldmaps share the BOLD PE axis "
            "(e.g., BOLD is 'j' but fieldmaps are 'i'/'k'). Check metadata."
        )

    return any_opposed


def collect_pe_dir(database: Database, c: str) -> str:
    database.fillmetadata("phase_encoding_direction", [c])
    pe_dir = canonicalize_direction_code(database.metadata(c, "phase_encoding_direction"), c)
    return pe_dir


def collect_fieldmaps(database: Database, bold_file_path: str, silent: bool = False) -> list[str]:
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
        "fieldmap": ["magnitude", "magnitude1", "magnitude2"],
    }

    incomplete: set[str] = set()

    for fmap_path in candidates:
        suffix = database.tagval(fmap_path, "suffix")
        assert isinstance(suffix, str)

        if suffix not in magnitude_map:
            continue

        valid_magnitude_suffixes = magnitude_map[suffix]

        has_magnitude = any(
            database.tagval(candidate_path, "suffix") in valid_magnitude_suffixes
            for candidate_path in candidates
        )

    if not has_magnitude:
        incomplete.add(fmap_path)

    if len(incomplete) > 0:
        if silent is not True:
            incomplete_str = pe.join(sorted(incomplete))
            logger.info(f"Skipping field maps {incomplete_str} due to missing magnitude images")
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

    try:
        bold_pe_dir = collect_pe_dir(database, bold_file_path)
    except ValueError:
        logger.warning(...)
        candidates -= set(c for c, _ in epi_fmaps)
    else:
        has_opposing = has_opposing_pe(epi_fmaps, bold_pe_dir)
        if not has_opposing:
            candidates -= set(c for c, _ in epi_fmaps)
        else:
            bold_axis, bold_sign = _pe_axis_sign(bold_pe_dir)
            candidates &= set(
                c for c, pe in epi_fmaps
                if _pe_axis_sign(pe)[0] == bold_axis
                and _pe_axis_sign(pe)[1] != bold_sign
            )

    return sorted(candidates)
