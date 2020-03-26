# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np
from scipy.io import loadmat
import pandas as pd

from ..spec import BoldTagsSchema, File


def extract(x):
    """
    Extract single value from n-dimensional array

    :param x: Array

    """
    if isinstance(x, np.ndarray):
        return extract(x[0])
    return x


def get_condition_files(analysis_obj, database):
    """
    returns dictionary bold image file path -> list of event file paths
    """
    tagdict = BoldTagsSchema().dump(analysis_obj.tags)
    bold_filepaths = database.get(**tagdict)
    if bold_filepaths is None:
        return
    event_filepaths = [
        database.get_events(filepath) for filepath in bold_filepaths.copy()
    ]
    return dict(zip(bold_filepaths, event_filepaths))


def parse_condition_files(eventfilepaths_dict, database):
    """
    Parse condition files into conditions, onsets and durations

    :param eventfilepaths_dict: dictionary bold image file path -> list of event file paths
    :param ext: EventsExtension

    """
    for bold_filepath, event_filepaths in eventfilepaths_dict.items():
        if isinstance(event_filepaths, str):
            fileobj = File(
                path=event_filepaths, tags=database.get_tags(event_filepaths)
            )
        else:
            fileobj = [
                File(path=filepath, tags=database.get_tags(filepath))
                for filepath in event_filepaths
            ]
        yield (bold_filepath, *parse_condition_file(fileobj))


def parse_condition_file(input):
    conditions = []
    onsets = []
    durations = []
    if isinstance(input, list) or isinstance(input, tuple):
        for fileobj in input:
            condition = fileobj.tags.condition
            assert condition is not None
            assert fileobj.tags.extension == "txt"
            data = np.loadtxt(fileobj.path)
            conditions.append(condition)
            onsets.append(data[:, 0].tolist())
            durations.append(data[:, 1].tolist())
    else:
        fileobj = input
        extension = fileobj.tags.extension
        filepath = fileobj.path
        if extension == "tsv":
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
        elif extension == "mat":
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
