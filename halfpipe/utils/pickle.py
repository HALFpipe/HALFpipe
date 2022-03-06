# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import gzip
import lzma
import pickle
import re
from io import BufferedIOBase
from pathlib import Path
from typing import Callable, Literal

from traits.trait_errors import TraitError

from . import logger
from .future import chdir
from .path import split_ext

pickle_lzma_extension = ".pickle.xz"


def load_pickle_lzma(file_path: str):
    if not file_path.endswith(pickle_lzma_extension):
        file_path = f"{file_path}{pickle_lzma_extension}"

    try:
        with lzma.open(file_path, "rb") as file_handle:
            return Unpickler(file_handle).load()

    except (lzma.LZMAError, TraitError, EOFError, AttributeError) as e:
        logger.error(f'Error while reading "{file_path}"', exc_info=e)
        return None


def dump_pickle_lzma(file_path: str, obj):
    if not file_path.endswith(pickle_lzma_extension):
        file_path = f"{file_path}{pickle_lzma_extension}"

    if Path(file_path).is_file():
        logger.warning(f'Overwriting existing file "{file_path}"')

    try:
        with lzma.open(file_path, "wb") as fptr:
            pickle.dump(obj, fptr, protocol=pickle.HIGHEST_PROTOCOL)

    except lzma.LZMAError as e:
        logger.error(f'Error while writing "{file_path}"', exc_info=e)


class Unpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        module = re.sub(r"^halfpipe\.workflow(?=\.|$)", "halfpipe.workflows", module)
        module = re.sub(r"^halfpipe\.interface(?=\.|$)", "halfpipe.interfaces", module)

        if module == "halfpipe.interfaces.stats.tsv":
            module = "halfpipe.interfaces.stats.design"

        return super(Unpickler, self).find_class(module, name)


def load_pickle(file_path: str | Path):
    file_path = Path(file_path)

    _, file_extension = split_ext(file_path)

    if file_extension == ".pkl":
        file_open: Callable[[Path, Literal["rb"]], BufferedIOBase] = open
    elif file_extension == ".pklz":
        file_open = gzip.open
    elif file_extension == ".pickle.xz":
        file_open = lzma.open
    else:
        raise ValueError()

    with chdir(file_path.parent):
        with file_open(file_path, "rb") as file_handle:
            return Unpickler(file_handle).load()


def patch_nipype_unpickler():
    from nipype.pipeline.engine import base, nodes, utils
    from nipype.utils import filemanip

    filemanip.loadpkl = load_pickle
    utils.loadpkl = load_pickle
    nodes.loadpkl = load_pickle
    base.loadpkl = load_pickle
