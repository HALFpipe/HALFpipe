# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nibabel.nifti1 import Nifti1Header

from ..model.setting import BaseSettingSchema
from .metadata.niftiheader import NiftiheaderLoader
from .metadata.direction import get_axcodes_set
from .bids import BidsDatabase, get_file_metadata
from .database import Database
from ..utils import logger, inflect_engine as pe
from ..utils.image import nvol


def collect_events(
    database: Database, sourcefile: str
) -> str | tuple[tuple[str, str], ...] | None:
    sourcefile_subject = database.tagval(sourcefile, "sub")

    candidates = database.associations(
        sourcefile,
        task=database.tagval(sourcefile, "task"),  # enforce same task
        datatype="func",
        suffix="events",
    )

    if candidates is None or len(candidates) == 0:
        return None

    candidates = sorted(set(candidates))  # remove duplicates

    def match_subject(event_file):
        subject = database.tagval(event_file, "sub")

        if subject is not None:
            return subject == sourcefile_subject
        else:
            return True

    condition_files = list(filter(match_subject, candidates))

    extensions = database.tagvalset("extension", filepaths=condition_files)
    assert extensions is not None

    if len(condition_files) == 0:
        return None  # we did not find any
    elif len(condition_files) == 1:
        if ".mat" in extensions or ".tsv" in extensions:
            return condition_files[0]

    if ".txt" in extensions:
        condition_tuples: list[tuple[str, str]] = list()

        for condition_file in condition_files:
            condition = database.tagval(condition_file, "condition")
            assert isinstance(condition, str)
            condition_tuples.append((condition_file, condition))

        return (*condition_tuples,)

    raise ValueError(f'Cannot collect condition files for "{sourcefile}"')


def collect_fieldmaps(database: Database, bold_file_path: str, silent: bool = False) -> list[str]:
    sub = database.tagval(bold_file_path, "sub")
    filters = dict(sub=sub)  # enforce same subject

    session = database.tagval(bold_file_path, "ses")
    if session is not None:  # enforce fmaps from same session
        filters.update(dict(ses=session))

    candidates = database.associations(bold_file_path, datatype="fmap", **filters)

    if candidates is None:
        return list()

    candidates = set(candidates)

    # filter

    magnitude = frozenset(["magnitude1", "magnitude2"])
    has_magnitude = any(database.tagval(c, "suffix") in magnitude for c in candidates)

    needs_magnitude = frozenset([
        "phasediff", "phase1", "phase2", "fieldmap",
    ])

    incomplete = set()
    for c in candidates:
        if database.tagval(c, "suffix") in needs_magnitude:
            if not has_magnitude:
                incomplete.add(c)

    if len(incomplete) > 0:
        if silent is not True:
            incomplete_str = pe.join(sorted(incomplete))
            logger.info(
                f"Skipping field maps {incomplete_str} due to missing magnitude images"
            )
        candidates -= incomplete

    return sorted(candidates)


def collect_bold_files(
    database, setting_factory, feature_factory
) -> dict[str, list[str]]:

    # find bold files

    bold_file_paths = setting_factory.sourcefiles | feature_factory.sourcefiles

    # filter

    bold_file_paths_dict = dict()

    for bold_file_path in bold_file_paths:

        sub = database.tagval(bold_file_path, "sub")
        t1ws = database.associations(
            bold_file_path,
            datatype="anat",
            sub=sub,
        )

        if t1ws is None:  # remove bold files without T1w
            continue

        associated_file_paths = [bold_file_path, *t1ws]

        fmaps = collect_fieldmaps(database, bold_file_path)
        if fmaps is not None:
            associated_file_paths.extend(fmaps)  # add all fmaps for now, filter later

        bold_file_paths_dict[bold_file_path] = associated_file_paths

    bold_file_paths = [b for b in bold_file_paths if b in bold_file_paths_dict]

    _bids_database = BidsDatabase(database)
    bids_dict: dict[str, set[str]] = dict()
    for bold_file_path in bold_file_paths:

        # check for duplicate tags via bids path as this contains all tags by definition

        bids_path = None

        try:
            _bids_database.put(bold_file_path)
            bids_path = _bids_database.tobids(bold_file_path)
        except ValueError:
            continue

        assert bids_path is not None

        if bids_path not in bids_dict:
            bids_dict[bids_path] = set()

        bids_dict[bids_path].add(bold_file_path)

    for bold_file_pathset in bids_dict.values():
        if len(bold_file_pathset) == 1:
            continue

        # remove duplicates by scan length
        # this is a heuristic based on the idea that duplicate scans may be
        # scans that were cancelled or had technical difficulties and therefore
        # had to be restarted

        nvol_dict = {
            bold_file_path: nvol(bold_file_path) for bold_file_path in bold_file_pathset
        }
        max_nvol = max(nvol_dict.values())
        selected = set(
            bold_file_path
            for bold_file_path, nvol in nvol_dict.items()
            if nvol == max_nvol
        )

        # if the heuristic above doesn't work, we just choose the alphabetically
        # last one

        if len(selected) > 1:
            last = sorted(selected)[-1]
            selected = set([last])

        (selectedbold_file_path,) = selected

        # log what happened

        message_strs = [
            f"Found {len(bold_file_pathset)-1:d} file with "
            f'identical tags to {selectedbold_file_path}":'
        ]

        bold_file_path = next(iter(bold_file_pathset))
        for bold_file_path in bold_file_pathset:
            if bold_file_path != selectedbold_file_path:
                message_strs.append(f'Excluding file "{bold_file_path}"')

        if nvol_dict[bold_file_path] < max_nvol:
            message_strs.append(
                "Decision criterion was: Image with the longest duration"
            )
        else:
            message_strs.append(
                "Decision criterion was: Last image when sorting alphabetically"
            )

        logger.warning("\n".join(message_strs))

        # remove excluded files

        for bold_file_path in bold_file_pathset:
            if bold_file_path != selectedbold_file_path:
                del bold_file_paths_dict[bold_file_path]

    bold_file_paths = [b for b in bold_file_paths if b in bold_file_paths_dict]

    return bold_file_paths_dict


def collect_metadata(database, source_file, setting) -> dict:
    metadata = dict(setting=BaseSettingSchema().dump(setting))

    metadata.update(get_file_metadata(database, source_file))

    header, _ = NiftiheaderLoader.load(source_file)
    assert isinstance(header, Nifti1Header)

    zooms = list(map(float, header.get_zooms()))
    assert all(isinstance(z, float) for z in zooms)
    metadata["acquisition_voxel_size"] = tuple(zooms[:3])

    data_shape = header.get_data_shape()
    assert len(data_shape) == 4
    metadata["acquisition_volume_shape"] = tuple(data_shape[:3])
    metadata["number_of_volumes"] = int(data_shape[3])

    (axcodes,) = get_axcodes_set(source_file)
    axcode_str = "".join(axcodes)
    metadata["acquisition_orientation"] = axcode_str

    return metadata
