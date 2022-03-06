# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import numpy as np
from scipy.io import loadmat

from ..model.file import File
from ..utils import logger
from ..utils.path import split_ext
from .spreadsheet import read_spreadsheet

bold_filedict = {"datatype": "func", "suffix": "bold"}


def parse_tsv_condition_file(filepath):
    conditions = []
    onsets = []
    durations = []

    data = read_spreadsheet(filepath)

    groupby = data.groupby(by="trial_type")

    conditions.extend(groupby.groups.keys())
    onset_dict = groupby["onset"].apply(list).to_dict()
    duration_dict = groupby["duration"].apply(list).to_dict()

    onsets.extend(onset_dict[c] for c in conditions)
    durations.extend(duration_dict[c] for c in conditions)

    return conditions, onsets, durations


def parse_mat_condition_file(filepath):
    def extract(x):
        """
        Extract single value from n-dimensional array
        """
        if isinstance(x, np.ndarray):
            return extract(x[0])
        return x

    conditions = []
    onsets = []
    durations = []

    data = loadmat(filepath)

    assert data is not None

    mnames = np.squeeze(data["names"])
    mdurations = np.squeeze(data["durations"])
    monsets = np.squeeze(data["onsets"])

    for i, name in enumerate(mnames):
        condition = extract(name)
        ionsets = np.ravel(monsets[i])
        idurations = np.ravel(mdurations[i])

        data = np.zeros((ionsets.size, 2))
        data[:, 0] = ionsets
        data[:, 1] = idurations

        conditions.append(condition)
        onsets.append(data[:, 0].tolist())
        durations.append(data[:, 1].tolist())

    return conditions, onsets, durations


def parse_txt_condition_files(filepaths, conditions):
    onsets = []
    durations = []
    for filepath, condition in zip(filepaths, conditions):
        assert condition is not None

        try:
            data_frame = read_spreadsheet(filepath)

            data_frame.rename(
                columns=dict(
                    zip(list(data_frame.columns)[:2], ["onsets", "durations"])
                ),
                inplace=True,
            )

            onsets.append(data_frame.onsets.tolist())
            durations.append(data_frame.durations.tolist())

        except Exception as e:  # unreadable or empty file
            logger.warning(f'Cannot read condition file "{filepath}"', exc_info=e)
            onsets.append([])  # fail gracefully
            durations.append([])

    return conditions, onsets, durations


def parse_condition_file(in_any=None):
    conditions = []
    onsets = []
    durations = []

    if isinstance(in_any, (list, tuple)):
        if all(
            isinstance(fileobj, File) and fileobj.extension == ".txt"
            for fileobj in in_any
        ):
            condition_file_tpls = [
                (fileobj.path, fileobj.tags.get("condition")) for fileobj in in_any
            ]
            filepaths, conditions = zip(*condition_file_tpls)
            return parse_txt_condition_files(filepaths, conditions)

        elif all(isinstance(tpl, (list, tuple)) and len(tpl) == 2 for tpl in in_any):
            filepaths, conditions = zip(*in_any)
            return parse_txt_condition_files(filepaths, conditions)

        elif len(in_any) == 1:
            (condition_file,) = in_any
            return parse_condition_file(condition_file)

        else:
            raise ValueError("Cannot read condition files")

    elif isinstance(in_any, (str, Path)):
        _, extension = split_ext(in_any)
        if extension == ".mat":
            return parse_mat_condition_file(in_any)
        else:
            return parse_tsv_condition_file(in_any)

    elif isinstance(in_any, File):
        fileobj = in_any
        extension = fileobj.extension
        filepath = fileobj.path
        if extension == ".tsv":
            return parse_tsv_condition_file(filepath)
        elif extension == ".mat":
            return parse_mat_condition_file(filepath)
        else:
            raise ValueError("Unknown extension")

    return conditions, onsets, durations
