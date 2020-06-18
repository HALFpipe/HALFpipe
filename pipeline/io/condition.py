# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from scipy.io import loadmat
import pandas as pd

# import h5py

from ..spec import BoldTagsSchema, File
from ..utils import first


def analysis_parse_condition_files(analysisobj, database):
    """
    returns generator for tuple event file paths, conditions, onsets, durations
    """
    tagdict = BoldTagsSchema().dump(analysisobj.tags)
    bold_filepaths = database.get(**tagdict)
    if bold_filepaths is None:
        return
    eventfile_dict = {
        filepath: database.get_associations(filepath, datatype="func", suffix="events")
        for filepath in bold_filepaths.copy()
    }
    eventfile_set = set(eventfile_dict.values())
    if len(eventfile_set) == 0 or None in eventfile_set:
        return
    for in_any in eventfile_set:
        if isinstance(in_any, str):
            fileobj = File(path=in_any, tags=database.get_tags(in_any))
        else:
            fileobj = [File(path=filepath, tags=database.get_tags(filepath)) for filepath in in_any]
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
        if all(isinstance(fileobj, File) and fileobj.tags.extension == "txt" for fileobj in in_any):
            condition_file_tpls = [(fileobj.path, fileobj.tags.condition) for fileobj in in_any]
            filepaths, conditions = zip(*condition_file_tpls)
            return parse_txt_condition_files(filepaths, conditions)
        elif all(len(fileobj) == 2 for fileobj in in_any):
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
        extension = fileobj.tags.extension
        filepath = fileobj.path
        if extension == "tsv":
            return parse_tsv_condition_file(filepath)
        elif extension == "mat":
            return parse_mat_condition_file(filepath)
        else:
            raise ValueError("Unknown extension")
    return conditions, onsets, durations
