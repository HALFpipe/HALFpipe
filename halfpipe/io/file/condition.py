# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from scipy.io import loadmat
import pandas as pd

from ...model import File
from ...utils import first

bold_filedict = {"datatype": "func", "suffix": "bold"}


def find_and_parse_condition_files(database, filters=None):
    """
    returns generator for tuple event file paths, conditions, onsets, durations
    """
    bold_filepaths = database.get(**bold_filedict)
    if bold_filepaths is None:
        return

    bold_filepaths = set(bold_filepaths)

    if filters is not None:
        bold_filepaths = database.applyfilters(bold_filepaths, filters)

    eventfile_dict = {
        filepath: database.associations(filepath, **{"datatype": "func", "suffix": "events"})
        for filepath in bold_filepaths.copy()
    }

    eventfile_set = set(eventfile_dict.values())
    if len(eventfile_set) == 0 or None in eventfile_set:
        return

    for in_any in eventfile_set:
        if isinstance(in_any, str):
            fileobj = File(path=database.fileobj(in_any), tags=database.tags(in_any))
        elif isinstance(in_any, (tuple, list, set)):
            fileobj = [database.fileobj(filepath) for filepath in in_any]
            assert all(f is not None for f in fileobj)
        else:
            raise ValueError(f'Unknown event file "{in_any}"')
        yield (in_any, *parse_condition_file(in_any=fileobj))


def parse_tsv_condition_file(filepath):
    conditions = []
    onsets = []
    durations = []
    dtype = {
        "subject_id": str,
        "session_id": str,
        "participant_id": str,
        "trial_type": str,
    }
    data = pd.read_csv(filepath, sep="\t", na_values="n/a", dtype=dtype)
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
    try:
        data = loadmat(filepath)
    except NotImplementedError:
        # with h5py
        raise
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
        data = np.loadtxt(filepath)
        onsets.append(data[:, 0].tolist())
        durations.append(data[:, 1].tolist())
    return conditions, onsets, durations


def parse_condition_file(in_any=None):
    conditions = []
    onsets = []
    durations = []
    if isinstance(in_any, (list, tuple)):
        if all(isinstance(fileobj, File) and fileobj.extension == ".txt" for fileobj in in_any):
            condition_file_tpls = [
                (fileobj.path, fileobj.tags.get("condition")) for fileobj in in_any
            ]
            filepaths, conditions = zip(*condition_file_tpls)
            return parse_txt_condition_files(filepaths, conditions)
        elif all(isinstance(tpl, (list, tuple)) and len(tpl) == 2 for tpl in in_any):
            filepaths, conditions = zip(*in_any)
            return parse_txt_condition_files(filepaths, conditions)
        elif len(in_any) == 1:
            return parse_condition_file(first(in_any))
        else:
            raise ValueError("Cannot read condition files")
    elif isinstance(in_any, str):
        try:
            return parse_mat_condition_file(in_any)
        except ValueError:
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
