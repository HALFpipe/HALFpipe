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
    if isinstance(obj, (str, dict)):
        return obj
    try:
        ret = []
        for val in obj:
            raveled_val = ravel(val)
            if not isinstance(raveled_val, (str, dict)):
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


def falsetoundefined(arr):
    """
    replace none with undefined
    """
    from traits.trait_base import _Undefined

    ret = []
    for val in arr:
        if not val:
            ret.append(_Undefined())
        else:
            ret.append(val)
    return ret
