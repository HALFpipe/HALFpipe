# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import List, Dict

from itertools import zip_longest
from math import isclose

import numpy as np

from ..io.index import BidsDatabase
from ..utils import logger, nvol, ravel
from ..io.metadata.niftiheader import NiftiheaderLoader
from ..io.metadata.sidecar import SidecarMetadataLoader


def _format_matrix_comparison(*args):

    lines = list(zip(*(
        np.array_str(a, precision=3, suppress_small=True).splitlines()
        for a in args
    )))

    max_str_len = max(len(a) for a in ravel(lines))

    for i, line in enumerate(lines):
        if i == len(lines) // 2:
            delimiter = "!="
        else:
            delimiter = "  "

        s = "    "
        for j, a in enumerate(line):
            if j > 0:
                s += f" {delimiter} "
            s += f"{a:{max_str_len}}"

        yield s


def collect_fieldmaps(database, bold_file_path, filters) -> List[str]:
    candidates = database.associations(
        bold_file_path, datatype="fmap", **filters
    )

    if candidates is None:
        return list()

    bold_header, _ = NiftiheaderLoader.load(bold_file_path)

    if bold_header is None:
        return list()

    bold_data_shape = bold_header.get_data_shape()[:3]
    bold_affine = bold_header.get_best_affine()[:3, :3]

    bold_sidecar = SidecarMetadataLoader.load_json(bold_file_path)
    shim_setting_key = "ShimSetting"
    bold_shim_setting = bold_sidecar.get(shim_setting_key)

    message_log_method = logger.debug
    message_strs = list()

    def match_metadata(candidate: str) -> bool:
        nonlocal message_log_method

        header, _ = NiftiheaderLoader.load(candidate)

        # match only the first three dimensions
        data_shape = header.get_data_shape()[:3]

        # match only the voxel size (zooms) and the skew, not the origin
        # because the images will be coregistered anyway to deal with
        # translation
        affine = header.get_best_affine()[:3, :3]

        if data_shape != bold_data_shape:
            message_log_method = logger.warning
            message_strs.append(
                f'Excluding "{candidate}" due to data shape '
                f"({data_shape} != {bold_data_shape})"
            )
            return False

        if not np.allclose(affine, bold_affine, atol=1e-1):
            message_log_method = logger.warning
            message_strs.append(
                f'Excluding "{candidate}" because the field map affine differs '
                "significantly from the bold affine matrix"
            )
            message_strs.extend(_format_matrix_comparison(affine, bold_affine))
            return False

        sidecar = SidecarMetadataLoader.load_json(candidate)

        shim_setting = sidecar.get(shim_setting_key)
        if shim_setting is not None and bold_shim_setting is not None:
            if any(
                not isclose(float(a), float(b), abs_tol=1e-2)
                for a, b in zip_longest(list(shim_setting), list(bold_shim_setting))
            ):
                message_log_method = logger.warning
                message_strs.append(
                    f'Including "{candidate}" even though shim settings differ significantly'
                    f"({list(shim_setting)} != {list(bold_shim_setting)})"
                )
                return True

        message_strs.append(
            f'Including "{candidate}"'
        )
        return True

    candidates = list(filter(match_metadata, candidates))

    if len(message_strs) > 0:
        message_strs.insert(
            0,
            f'Assigning field maps for "{bold_file_path}" using heuristic',
        )
        message_log_method("\n".join(message_strs))

    return candidates


def collect_bold_files(database, setting_factory, feature_factory) -> Dict[str, List[str]]:

    # find bold files

    bold_file_paths = setting_factory.sourcefiles | feature_factory.sourcefiles

    # filter

    bold_file_paths_dict = dict()

    for bold_file_path in bold_file_paths:

        sub = database.tagval(bold_file_path, "sub")
        filters = dict(sub=sub)  # enforce same subject

        t1ws = database.associations(
            bold_file_path, datatype="anat", **filters
        )

        if t1ws is None:  # remove bold files without T1w
            continue

        associated_file_paths = [bold_file_path, *t1ws]

        session = database.tagval(bold_file_path, "ses")
        if session is not None:  # enforce fmaps from same session
            filters.update(dict(ses=session))

        fmaps = collect_fieldmaps(database, bold_file_path, filters)
        if fmaps is not None:
            associated_file_paths.extend(fmaps)  # add all fmaps for now, filter later

        bold_file_paths_dict[bold_file_path] = associated_file_paths

    bold_file_paths = [b for b in bold_file_paths if b in bold_file_paths_dict]

    _bids_database = BidsDatabase(database)
    bids_dict = dict()
    for bold_file_path in bold_file_paths:

        # check for duplicate tags via bids path as this contains all tags by definition

        _bids_database.put(bold_file_path)

        bids_path = _bids_database.tobids(bold_file_path)

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
            bold_file_path: nvol(bold_file_path)
            for bold_file_path in bold_file_pathset
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
