# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Any

from pathlib import Path
import lzma
import pickle
from traits.trait_errors import TraitError

from ..utils import logger

pickle_lzma_extension = ".pickle.xz"


def load_pickle_lzma(file_path: str):
    if not file_path.endswith(pickle_lzma_extension):
        file_path = f"{file_path}{pickle_lzma_extension}"

    try:
        with lzma.open(file_path, "rb") as fptr:
            return pickle.load(fptr)

    except (lzma.LZMAError, TraitError, EOFError, AttributeError) as e:
        logger.error(f'Error while reading "{file_path}"', exc_info=e)
        return None


def dump_pickle_lzma(file_path: str, obj: Any):
    if not file_path.endswith(pickle_lzma_extension):
        file_path = f"{file_path}{pickle_lzma_extension}"

    if Path(file_path).is_file():
        logger.warning(f'Overwriting existing file "{file_path}"')

    try:
        with lzma.open(file_path, "wb") as fptr:
            pickle.dump(obj, fptr, protocol=pickle.HIGHEST_PROTOCOL)

    except lzma.LZMAError as e:
        logger.error(f'Error while writing "{file_path}"', exc_info=e)
