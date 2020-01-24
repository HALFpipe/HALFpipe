# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import pathlib

import nibabel as nib
import numpy as np


def _splitext(fname):
    """Splits filename and extension (.gz safe)
    >>> splitext('some/file.nii.gz')
    ('file', '.nii.gz')
    >>> splitext('some/other/file.nii')
    ('file', '.nii')
    >>> splitext('otherext.tar.gz')
    ('otherext', '.tar.gz')
    >>> splitext('text.txt')
    ('text', '.txt')

    Source: niworkflows
    """
    from pathlib import Path
    basename = str(Path(fname).name)
    stem = Path(basename.rstrip('.gz')).stem
    return stem, basename[len(stem):]


def get_first(l):
    """
    get first element from list
    doesn't fail is input is not a list

    :param l: input list

    """
    if not isinstance(l, list):
        return l
    else:
        return get_first(l[0])


def firstval(dict):
    """
    get first value from dict
    """
    return next(iter(dict.values()))


def get_path(path, EXT_PATH):
    path = path.strip()

    if path.startswith("/"):
        path = path[1:]

    path = os.path.join(EXT_PATH, path)

    return path


def deepvalues(l):
    """
    Return values of a dictionary, recursive

    :param l: Input dictionary

    """
    if isinstance(l, str):
        return [l]
    else:
        o = []
        for k in l.values():
            o += deepvalues(k)
        return o


def _ravel(in_val):
    if not isinstance(in_val, list):
        return in_val
    flat_list = []
    for val in in_val:
        raveled_val = _ravel(val)
        if isinstance(raveled_val, (tuple, list)):
            flat_list.extend(raveled_val)
        else:
            flat_list.append(raveled_val)
    return flat_list


def get_float(input):
    def flatten(l):
        if isinstance(l, str) or isinstance(l, float):
            return [l]
        else:
            o = []
            for k in l:
                o += flatten(k)
            return o
    return float(flatten(input)[0])


def transpose(d):
    """
    Transpose a dictionary

    :param d: Input dictionary

    """
    out = dict()
    for key0, value0 in d.items():
        for key1, value1 in value0.items():
            if key1 not in out:
                out[key1] = dict()
            while isinstance(value1, dict) and \
                    len(value1) == 1 and "" in value1:
                value1 = value1[""]
            out[key1][key0] = value1
    return out


def lookup(d, subject_id=None, run_id=None, condition_id=None):
    """
    Look up value in a three-level dictionary based on three keys

    :param d: Input dictionary
    :param subject_id: Outer key (Default value = None)
    :param run_id: Middle key (Default value = None)
    :param condition_id: Inner key (Default value = None)

    """
    key0 = []
    if isinstance(d, dict) and len(d) == 1 and "" in d:
        key0.append("")
    elif subject_id is None:
        key0 += list(d.keys())
    else:
        key0.append(subject_id)

    if not key0[0] in d:
        return None

    e = d[key0[0]]

    key1 = []
    if isinstance(e, dict) and len(e) == 1 and "" in e:
        key1.append("")
    elif run_id is None:
        key1 += list(e.keys())
    else:
        key1.append(run_id)

    if not key1[0] in e:
        return None

    f = e[key1[0]]

    key2 = []
    if isinstance(f, dict) and len(f) == 1 and "" in f:
        key2.append("")
    elif condition_id is None:
        key2 += list(f.keys())
    else:
        key2.append(condition_id)

    o = dict()
    for i in key0:
        o[i] = dict()
        for j in key1:
            o[i][j] = dict()
            for k in key2:
                o[i][j][k] = d[i][j][k]

    def flatten(dd):
        """
        Flatten a dictionary

        :param dd: Input dictionary

        """
        if isinstance(dd, dict):
            if len(dd) == 1:
                return flatten(next(iter(dd.values())))
            return {k: flatten(v) for k, v in dd.items()}
        return dd
    return flatten(o)


def create_directory(directory_path):
    directory = pathlib.Path(directory_path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory_path


def nonzero_atlas(atlas_image_path, seg_image_path):
    """

    :param atlas_image_path: atlas_file
    :param seg_image_path: image file to be compared
    :return:
    """
    input_image = seg_image_path
    in_img = nib.load(input_image)
    in_data = in_img.get_data()
    # binarize image
    in_data[in_data != 0] = 1

    seg_img = nib.load(atlas_image_path)
    seg_data = seg_img.get_data()

    masked = np.zeros_like(seg_data)
    masked[in_data != 0] = seg_data[in_data != 0]

    in_data = in_data.astype(np.uint8)

    label_number = []
    size_roi_data = []
    size_roi_atlas = []

    for label in np.unique(seg_data):
        if int(label) > 0:
            label_number.append(label)
            size_roi_data.append(int(seg_data[masked == label].shape[0]))
            size_roi_atlas.append(int(seg_data[seg_data == label].shape[0]))

    out_arr = np.column_stack((label_number, size_roi_data))
    out_arr = np.column_stack((out_arr, size_roi_atlas))

    # column1, column2, column3
    # Label, n_data, n_atlas
    return out_arr
