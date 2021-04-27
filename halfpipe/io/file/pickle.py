# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import lzma
import pickle
from traits.trait_errors import TraitError
from pathlib import Path

from ...utils import logger


def loadpicklelzma(filepath):
    try:
        with lzma.open(filepath, "rb") as fptr:
            return pickle.load(fptr)
    except (lzma.LZMAError, TraitError) as e:
        logger.error(f'Error while reading "{filepath}"', exc_info=e)


def dumppicklelzma(filepath, obj):
    try:
        with lzma.open(filepath, "wb") as fptr:
            pickle.dump(obj, fptr)
    except lzma.LZMAError as e:
        logger.error(f'Error while writing "{filepath}"', exc_info=e)


def uncacheobj(workdir, typestr, uuid, typedisplaystr=None):
    if typedisplaystr is None:
        typedisplaystr = typestr
    path = Path(workdir) / make_cachefilepath(typestr, uuid)
    if path.exists():
        obj = loadpicklelzma(path)
        if uuid is not None and hasattr(obj, "uuid"):
            objuuid = getattr(obj, "uuid")
            if objuuid is None or objuuid != uuid:
                return
        logger.info(f"Cached {typedisplaystr} from {path}")
        return obj


def make_cachefilepath(typestr, uuid):
    if uuid is not None:
        uuidstr = str(uuid)[:8]
        path = f"{typestr}.{uuidstr}.pickle.xz"
    else:
        path = f"{typestr}.pickle.xz"
    return path


def cacheobj(workdir, typestr, obj, uuid=None):
    if uuid is None:
        uuid = getattr(obj, "uuid", None)
    path = Path(workdir) / make_cachefilepath(typestr, uuid)
    if path.exists():
        logger.warning(f"Overwrite {path}")
    dumppicklelzma(path, obj)
