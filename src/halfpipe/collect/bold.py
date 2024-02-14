# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..ingest.bids import BidsDatabase
from ..logging import logger
from ..utils.image import nvol
from .fmap import collect_fieldmaps


def collect_bold_files(database, post_processing_factory, feature_factory) -> dict[str, list[str]]:
    # find bold files

    bold_file_paths: set[str] = post_processing_factory.source_files | feature_factory.source_files
    bold_file_paths_dict: dict[str, list[str]] = dict()

    # filter
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

        sbrefs = database.associations(
            bold_file_path,
            datatype="func",
            suffix="sbref",
            sub=sub,
        )
        if sbrefs is not None:
            associated_file_paths.extend(sbrefs)

        bold_file_paths_dict[bold_file_path] = associated_file_paths

    bold_file_paths &= bold_file_paths_dict.keys()

    # check for duplicate tags via bids path as this contains all tags by definition
    _bids_database = BidsDatabase(database)
    bids_dict: dict[str, set[str]] = dict()
    for bold_file_path in bold_file_paths:
        bids_path = None

        try:
            _bids_database.put(bold_file_path)
            bids_path = _bids_database.to_bids(bold_file_path)
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

        nvol_dict = {bold_file_path: nvol(bold_file_path) for bold_file_path in bold_file_pathset}
        max_nvol = max(nvol_dict.values())
        selected = set(bold_file_path for bold_file_path, nvol in nvol_dict.items() if nvol == max_nvol)

        # if the heuristic above doesn't work, we just choose the alphabetically
        # last one

        if len(selected) > 1:
            last = sorted(selected)[-1]
            selected = set([last])

        (selectedbold_file_path,) = selected

        # log what happened

        message_strs = [f"Found {len(bold_file_pathset)-1:d} file with " f'identical tags to {selectedbold_file_path}":']

        bold_file_path = next(iter(bold_file_pathset))
        for bold_file_path in bold_file_pathset:
            if bold_file_path != selectedbold_file_path:
                message_strs.append(f'Excluding file "{bold_file_path}"')

        if nvol_dict[bold_file_path] < max_nvol:
            message_strs.append("Decision criterion was: Image with the longest duration")
        else:
            message_strs.append("Decision criterion was: Last image when sorting alphabetically")

        logger.warning("\n".join(message_strs))

        # remove excluded files

        for bold_file_path in bold_file_pathset:
            if bold_file_path != selectedbold_file_path:
                del bold_file_paths_dict[bold_file_path]

    return bold_file_paths_dict
