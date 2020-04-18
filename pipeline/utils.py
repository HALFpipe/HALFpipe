# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import lzma
import pickle
from os import path as op


def niftidim(input, idim):
    if isinstance(input, str):
        import nibabel as nib

        input = nib.load(input)
    if len(input.shape) > idim:
        return input.shape[idim]
    else:
        return 1


def nvol(input):
    from pipeline.utils import niftidim

    return niftidim(input, 3)


def splitext(fname):
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
    stem = Path(basename.rstrip(".gz")).stem
    return stem, basename[len(stem) :]


def first(obj):
    """
    get first element from iterable
    """
    if isinstance(obj, str):  # don't want to get letters from strings
        return obj
    try:
        return next(iter(obj))
    except TypeError:
        return obj
    except StopIteration:
        return  # return None on empty list


def second(obj):
    """
    get second element from iterable
    """
    try:
        it = iter(obj)
        next(it)
        return next(it)
    except TypeError:
        return obj
    except StopIteration:
        return  # return None on empty list


def firsttrait(obj):
    """
    get first element from iterable, or undefined

    :param obj: input list

    """
    try:
        return next(iter(obj))
    except TypeError:
        pass
    except StopIteration:
        pass
    from traits.trait_base import _Undefined

    return _Undefined()


def firstfloat(obj):
    """
    get first element from iterable
    """
    try:
        return float(next(iter(obj)))
    except ValueError:
        raise
    except TypeError:
        return obj
    except StopIteration:
        return  # return None on empty list


def firstval(dict):
    """
    get first value from dict
    """

    return first(dict.values())


def ravel(obj):
    if isinstance(obj, str):
        return obj
    try:
        ret = []
        for val in obj:
            raveled_val = ravel(val)
            if not isinstance(raveled_val, str):
                try:
                    ret.extend(raveled_val)
                    continue
                except TypeError:
                    pass
            ret.append(raveled_val)
        return ret
    except TypeError:
        return obj
    except StopIteration:
        return []  # empty input
    return ret


def hexdigest(obj):
    import hashlib

    m = hashlib.sha1()
    m.update(pickle.dumps(obj))
    return m.hexdigest()[:8]


def loadpicklelzma(filepath):
    try:
        with lzma.open(filepath, "rb") as fptr:
            return pickle.load(fptr)
    except lzma.LZMAError:
        pass


def savepicklelzma(filepath, obj):
    try:
        with lzma.open(filepath, "wb") as fptr:
            pickle.dump(obj, fptr)
    except lzma.LZMAError:
        pass


def uncacheobj(workdir, typestr, uuid):
    if uuid is not None:
        uuidstr = str(uuid)[:8]
        path = op.join(workdir, f"{typestr}.{uuidstr}.pickle.xz")
        if op.isfile(path):
            obj = loadpicklelzma(path)
            if hasattr(obj, "uuid"):
                objuuid = getattr(obj, "uuid")
                if objuuid is None or objuuid != uuid:
                    return
            logging.getLogger("pipeline").info(f"Using cached {typestr} from {path}")
            return obj
    else:
        path = op.join(workdir, f"{typestr}.pickle.xz")
        return loadpicklelzma(path)


def cacheobj(workdir, typestr, obj, uuid=None):
    if uuid is None:
        uuid = getattr(obj, "uuid", None)
    if uuid is not None:
        uuidstr = str(uuid)[:8]
        path = op.join(workdir, f"{typestr}.{uuidstr}.pickle.xz")
    else:
        path = op.join(workdir, f"{typestr}.pickle.xz")
    if op.isfile(path):
        logging.getLogger("pipeline").warn(f"Overwrite {path}")
    savepicklelzma(path, obj)


def readtsv(in_file):
    import numpy as np

    try:
        in_array = np.genfromtxt(in_file, missing_values="NaN,n/a,NA")
        return in_array
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(in_file, skip_header=1, missing_values="NaN,n/a,NA")
        return in_array
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(in_file, delimiter=",", missing_values="NaN,n/a,NA")
        return in_array
    except ValueError:
        pass
    try:
        in_array = np.genfromtxt(
            in_file, delimiter=",", skip_header=1, missing_values="NaN,n/a,NA"
        )
        return in_array
    except ValueError as e:
        logging.getLogger("pipeline").exception(f"Could not load file {in_file}", e)
        raise


def ncol(in_file):
    from pipeline.utils import readtsv

    return readtsv(in_file).shape[1]


def rank(in_file):
    import numpy as np
    from pipeline.utils import readtsv

    return np.linalg.matrix_rank(readtsv(in_file))


def noderivativeentitiesdict(indict):
    from pipeline.spec import derivative_entities

    return {k: v for k, v in indict.items() if k not in derivative_entities}


def onlyboldentitiesdict(indict):
    from pipeline.spec import bold_entities

    return {k: v for k, v in indict.items() if k in bold_entities}


def maplen(arrarr):
    """
    length of each sub-list
    """
    return list(map(len, arrarr))


#
# def _omit_first(l):
#     """
#     omit first element from list
#     doesn't fail is input is not a list
#
#     :param l: input list
#
#     """
#     if not isinstance(l, list):
#         return l
#     else:
#         return l[1:]
#
#

#
#
# def get_path(path, EXT_PATH):
#     path = path.strip()
#
#     if path.startswith("/"):
#         path = path[1:]
#
#     path = os.path.join(EXT_PATH, path)
#
#     return path
#
#
# def deepvalues(l):
#     """
#     Return values of a dictionary, recursive
#
#     :param l: Input dictionary
#
#     """
#     if isinstance(l, str):
#         return [l]
#     else:
#         o = []
#         for k in l.values():
#             o += deepvalues(k)
#         return o
#
#

#
#
# def transpose(d):
#     """
#     Transpose a dictionary
#
#     :param d: Input dictionary
#
#     """
#     out = dict()
#     for key0, value0 in d.items():
#         for key1, value1 in value0.items():
#             if key1 not in out:
#                 out[key1] = dict()
#             while isinstance(value1, dict) and len(value1) == 1 and "" in value1:
#                 value1 = value1[""]
#             out[key1][key0] = value1
#     return out
#
#
# def lookup(d, subject_id=None, run_id=None, condition_id=None):
#     """
#     Look up value in a three-level dictionary based on three keys
#
#     :param d: Input dictionary
#     :param subject_id: Outer key (Default value = None)
#     :param run_id: Middle key (Default value = None)
#     :param condition_id: Inner key (Default value = None)
#
#     """
#     key0 = []
#     if isinstance(d, dict) and len(d) == 1 and "" in d:
#         key0.append("")
#     elif subject_id is None:
#         key0 += list(d.keys())
#     else:
#         key0.append(subject_id)
#
#     if not key0[0] in d:
#         return None
#
#     e = d[key0[0]]
#
#     key1 = []
#     if isinstance(e, dict) and len(e) == 1 and "" in e:
#         key1.append("")
#     elif run_id is None:
#         key1 += list(e.keys())
#     else:
#         key1.append(run_id)
#
#     if not key1[0] in e:
#         return None
#
#     f = e[key1[0]]
#
#     key2 = []
#     if isinstance(f, dict) and len(f) == 1 and "" in f:
#         key2.append("")
#     elif condition_id is None:
#         key2 += list(f.keys())
#     else:
#         key2.append(condition_id)
#
#     o = dict()
#     for i in key0:
#         o[i] = dict()
#         for j in key1:
#             o[i][j] = dict()
#             for k in key2:
#                 o[i][j][k] = d[i][j][k]
#
#     def flatten(dd):
#         """
#         Flatten a dictionary
#
#         :param dd: Input dictionary
#
#         """
#         if isinstance(dd, dict):
#             if len(dd) == 1:
#                 return flatten(next(iter(dd.values())))
#             return {k: flatten(v) for k, v in dd.items()}
#         return dd
#
#     return flatten(o)
#
#
# def create_directory(directory_path):
#     directory = pathlib.Path(directory_path)
#     directory.mkdir(parents=True, exist_ok=True)
#     return directory_path
#
#
# def nonzero_atlas(atlas_image_path, seg_image_path):
#     """
#
#     :param atlas_image_path: atlas_file
#     :param seg_image_path: image file to be compared
#     :return:
#     """
#     input_image = seg_image_path
#     in_img = nib.load(input_image)
#     in_data = in_img.get_data()
#     # binarize image
#     in_data[in_data != 0] = 1
#
#     seg_img = nib.load(atlas_image_path)
#     seg_data = seg_img.get_data()
#
#     masked = np.zeros_like(seg_data)
#     masked[in_data != 0] = seg_data[in_data != 0]
#
#     in_data = in_data.astype(np.uint8)
#
#     label_number = []
#     size_roi_data = []
#     size_roi_atlas = []
#
#     for label in np.unique(seg_data):
#         if int(label) > 0:
#             label_number.append(label)
#             size_roi_data.append(int(seg_data[masked == label].shape[0]))
#             size_roi_atlas.append(int(seg_data[seg_data == label].shape[0]))
#
#     out_arr = np.column_stack((label_number, size_roi_data))
#     out_arr = np.column_stack((out_arr, size_roi_atlas))
#
#     # column1, column2, column3
#     # Label, n_data, n_atlas
#     return out_arr
