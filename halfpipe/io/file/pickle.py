# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional

import lzma
import pickle
from uuid import UUID
from traits.trait_errors import TraitError
from pathlib import Path

from ...utils import logger


def load_pickle_lzma(filepath):
    try:
        with lzma.open(filepath, "rb") as fptr:
            return pickle.load(fptr)
    except (lzma.LZMAError, TraitError, EOFError) as e:
        logger.error(f'Error while reading "{filepath}"', exc_info=e)


def dump_pickle_lzma(filepath, obj):
    try:
        with lzma.open(filepath, "wb") as fptr:
            pickle.dump(obj, fptr)
    except lzma.LZMAError as e:
        logger.error(f'Error while writing "{filepath}"', exc_info=e)


def _make_cache_file_path(type_str: str, uuid: Optional[UUID]):
    if uuid is not None:
        uuidstr = str(uuid)[:8]
        path = f"{type_str}.{uuidstr}.pickle.xz"
    else:
        path = f"{type_str}.pickle.xz"
    return path


def uncache_obj(workdir, type_str: str, uuid: UUID, display_str: str = None):
    if display_str is None:
        display_str = type_str
    path = Path(workdir) / _make_cache_file_path(type_str, uuid)
    if path.exists():
        obj = load_pickle_lzma(path)
        if uuid is not None and hasattr(obj, "uuid"):
            objuuid = getattr(obj, "uuid")
            if objuuid is None or str(objuuid) != str(uuid):
                return
        logger.info(f"Cached {display_str} from {path}")
        return obj


def cache_obj(workdir, typestr, obj, uuid=None):
    if uuid is None:
        uuid = getattr(obj, "uuid", None)
    path = Path(workdir) / _make_cache_file_path(typestr, uuid)
    if path.exists():
        logger.warning(f"Overwrite {path}")
    dump_pickle_lzma(path, obj)
