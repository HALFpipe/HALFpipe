# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


import gzip
import lzma
import pickle
from pathlib import Path
from typing import Callable

import pytest
from halfpipe.utils.pickle import load_pickle


@pytest.mark.parametrize(
    ("file_names", "function_mode"),
    (
        ("test.pkl", open),
        ("test.pklz", gzip.open),
        ("test.pickle.xz", lzma.open),
    ),
)
def test_load_pickle(tmp_path: Path, file_names: str, function_mode: Callable) -> None:
    test_list = ["hello", "world"]

    with function_mode(tmp_path / file_names, "wb") as f:
        pickle.dump(test_list, f)
    assert load_pickle(tmp_path / file_names) == test_list
