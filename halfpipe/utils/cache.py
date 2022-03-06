# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pickle
from pathlib import Path
from shelve import open as open_shelf
from typing import Any, Mapping, Optional, Union
from uuid import UUID

from ..utils import logger
from .pickle import dump_pickle_lzma, load_pickle_lzma


def _make_cache_file_path(type_str: str, uuid: Optional[Union[UUID, str]]):
    if uuid is not None:
        uuidstr = str(uuid)[:8]
        path = f"{type_str}.{uuidstr}"
    else:
        path = f"{type_str}"
    return path


def uncache_obj(
    workdir: Union[Path, str],
    type_str: str,
    uuid: Union[UUID, str],
    display_str: str = None,
):
    if display_str is None:
        display_str = type_str

    cache_file_path = str(Path(workdir) / _make_cache_file_path(type_str, uuid))

    try:
        obj = load_pickle_lzma(cache_file_path)

        if obj is not None:
            if uuid is not None and hasattr(obj, "uuid"):
                obj_uuid = getattr(obj, "uuid")
                if obj_uuid is None or str(obj_uuid) != str(uuid):
                    return None

            logger.info(f"Using {display_str} from cache at {cache_file_path}")

            return obj

    except Exception:
        pass

    try:
        return open_shelf(cache_file_path, flag="r")

    except Exception:
        pass

    return None


def cache_obj(
    workdir: Union[Path, str],
    type_str: str,
    obj: Any,
    uuid: Optional[Union[UUID, str]] = None,
):
    if uuid is None:
        uuid = getattr(obj, "uuid", None)

    cache_file_path = str(Path(workdir) / _make_cache_file_path(type_str, uuid))

    if isinstance(obj, Mapping):
        with open_shelf(
            cache_file_path, flag="n", protocol=pickle.HIGHEST_PROTOCOL, writeback=True
        ) as shelf:
            shelf.update(obj)

    else:
        dump_pickle_lzma(cache_file_path, obj)
