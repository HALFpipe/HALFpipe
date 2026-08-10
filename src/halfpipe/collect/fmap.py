# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..ingest.database import Database
from ..ingest.metadata.direction import canonicalize_direction_code
from ..logging import logger
from ..utils.format import inflect_engine as pe


class PhaseEncodingDirection(str):
    @property
    def axis(self) -> str:
        """
        Axis of the phase encoding direction
        """
        if not self:
            raise ValueError("Empty PhaseEncodingDirection")
        return self[0]

    @property
    def sign(self) -> str:
        """
        Sign of the phase encoding direction
        """
        return "-" if self.endswith("-") else "+"


def check_opposing_pe(
    epi_fmaps: list[tuple[str, PhaseEncodingDirection]], bold_pe_dir: PhaseEncodingDirection
) -> tuple[bool, bool]:
    has_same_axis = False
    has_opposing_pe = False

    for _, fmap_pe_dir in epi_fmaps:
        if fmap_pe_dir.axis != bold_pe_dir.axis:
            continue
        has_same_axis = True
        if fmap_pe_dir.sign != bold_pe_dir.sign:
            has_opposing_pe = True

    return has_opposing_pe, has_same_axis


def collect_pe_dir(database: Database, candidate: str) -> PhaseEncodingDirection:
    database.fillmetadata("phase_encoding_direction", [candidate])
    return PhaseEncodingDirection(
        canonicalize_direction_code(database.metadata(candidate, "phase_encoding_direction"), candidate)
    )


required_metadata: dict[str, list[str]] = {
    "epi": ["total_readout_time"],
    "fieldmap": ["units"],
    "phasediff": ["echo_time1", "echo_time2"],
    "phase1": ["echo_time"],
    "phase2": ["echo_time"],
}


def check_required_metadata(database: Database, candidate: str) -> list[str]:
    suffix = database.tagval(candidate, "suffix")
    if not isinstance(suffix, str):
        return list()
    missing = list()
    for key in required_metadata.get(suffix, list()):
        database.fillmetadata(key, [candidate])
        if database.metadata(candidate, key) is None:
            missing.append(key)
    return missing


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
            database.tagval(candidate_path, "suffix") in valid_magnitude_suffixes for candidate_path in candidates
        )

        if not has_magnitude:
            incomplete.add(fmap_path)

    if len(incomplete) > 0:
        if silent is not True:
            incomplete_str = pe.join(sorted(incomplete))
            logger.info(f"Skipping field maps {incomplete_str} due to missing magnitude images")
        candidates -= incomplete

    # Filter EPI (blip-up blip-down)
    epi_fmaps: list[tuple[str, PhaseEncodingDirection]] = list()
    for candidate in candidates:
        suffix = database.tagval(candidate, "suffix")
        if not isinstance(suffix, str):
            continue
        if suffix != "epi":
            continue

        epi_fmaps.append((candidate, collect_pe_dir(database, candidate)))

    if epi_fmaps:
        has_opposing_pe = False
        message: str = ""
        incomplete_str = pe.join(sorted(f'"{c}" with direction "{dir}"' for c, dir in epi_fmaps))
        try:
            bold_pe_dir = collect_pe_dir(database, bold_file_path)
        except ValueError:
            message = (
                f'Could not detect phase encoding direction for BOLD image "{bold_file_path}", so EPI (blip-up blip-down) '
                f"field maps {incomplete_str} cannot be used. Please check the metadata of the BOLD image"
            )
        else:  # No error
            has_opposing_pe, has_same_axis = check_opposing_pe(epi_fmaps, bold_pe_dir)
            if not has_same_axis:
                message = (
                    f"Skipping EPI (blip-up blip-down) field maps {incomplete_str} because they do not share "
                    f'the same phase encoding axis as the BOLD image "{bold_file_path}" with direction "{bold_pe_dir}"'
                )
            elif not has_opposing_pe:
                message = (
                    f"Skipping EPI (blip-up blip-down) field maps {incomplete_str} because they do not have "
                    f'a set of opposing phase encoding directions to the BOLD image "{bold_file_path}" with '
                    f'direction "{bold_pe_dir}"'
                )

        if has_opposing_pe:
            # Keep only EPI (blip-up blip-down)  field maps on the BOLD phase encoding axis
            candidates.difference_update(
                candidate for candidate, candidate_pe_dir in epi_fmaps if candidate_pe_dir.axis != bold_pe_dir.axis
            )
        else:
            candidates.difference_update(candidate for candidate, _ in epi_fmaps)
            if not silent:
                logger.warning(message)

    # Drop field maps that are missing metadata
    for candidate in list(candidates):
        missing = check_required_metadata(database, candidate)
        if not missing:
            continue
        candidates.remove(candidate)
        if not silent:
            logger.warning(
                f'Skipping field map "{candidate}" because it is missing the required metadata {pe.join(sorted(missing))}.'
            )

    return sorted(candidates)
