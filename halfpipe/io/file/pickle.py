# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import lzma
import pickle
from pathlib import Path


def loadpicklelzma(filepath):
    try:
        with lzma.open(filepath, "rb") as fptr:
            return pickle.load(fptr)
    except lzma.LZMAError:
        pass


def dumppicklelzma(filepath, obj):
    try:
        with lzma.open(filepath, "wb") as fptr:
            pickle.dump(obj, fptr)
    except lzma.LZMAError:
        pass


def uncacheobj(workdir, typestr, uuid, typedisplaystr=None):
    if typedisplaystr is None:
        typedisplaystr = typestr
    if uuid is not None:
        uuidstr = str(uuid)[:8]
        path = Path(workdir) / f"{typestr}.{uuidstr}.pickle.xz"
        if path.exists():
            obj = loadpicklelzma(path)
            if hasattr(obj, "uuid"):
                objuuid = getattr(obj, "uuid")
                if objuuid is None or objuuid != uuid:
                    return
            logging.getLogger("halfpipe").info(f"Using cached {typedisplaystr} from {path}")
            return obj
    else:
        path = Path(workdir) / f"{typestr}.pickle.xz"
        return loadpicklelzma(path)


def cacheobj(workdir, typestr, obj, uuid=None):
    if uuid is None:
        uuid = getattr(obj, "uuid", None)
    if uuid is not None:
        uuidstr = str(uuid)[:8]
        path = Path(workdir) / f"{typestr}.{uuidstr}.pickle.xz"
    else:
        path = Path(workdir) / f"{typestr}.pickle.xz"
    if path.exists():
        logging.getLogger("halfpipe").warn(f"Overwrite {path}")
    dumppicklelzma(path, obj)
