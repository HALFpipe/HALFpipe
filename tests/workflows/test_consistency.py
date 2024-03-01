# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from pathlib import Path

import pytest

from .datasets import Dataset, datasets, download_dataset


@pytest.mark.parametrize("dataset", datasets)
def test_data(tmp_path: Path, dataset: Dataset):
    # Check if the consistency_data directory exists
    logging.getLogger().setLevel(logging.CRITICAL)

    file = download_dataset(tmp_path, dataset)

    assert Path(file.path).exists(), "Consistency data directory does not exist"
    logging.getLogger().setLevel(logging.INFO)

    # add checks
    # - Verify the number of files
    # - Check for the existence of specific files
    # - Perform some checks on the contents of the files
