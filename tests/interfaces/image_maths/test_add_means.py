# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from random import seed

import numpy as np
import pandas as pd

from halfpipe.ingest.spreadsheet import read_spreadsheet
from halfpipe.interfaces.image_maths.add_means import AddMeans


def test_add_means_tsv(tmp_path):
    seed(a=0x5E6128C4)

    m = 100
    n = 5

    column_names = [f"column_{i + 1}" for i in range(n)]

    data_frame = pd.DataFrame(np.random.rand(m, n), columns=column_names)

    data_file = tmp_path / "data.tsv"
    data_frame.to_csv(data_file, sep="\t", header=True, index=False)

    demean_frame = data_frame - data_frame.mean()
    demean_file = tmp_path / "demean.tsv"
    demean_frame.to_csv(demean_file, sep="\t", header=True, index=False)

    add_means = AddMeans(
        in_file=demean_file,
        mean_file=data_file,
    )

    cwd = tmp_path / "add_means"
    cwd.mkdir()

    result = add_means.run(cwd=cwd)
    assert result.outputs is not None

    test_data_frame = read_spreadsheet(result.outputs.out_file)
    assert np.allclose(test_data_frame.values, data_frame.values)
    assert list(test_data_frame.columns) == list(data_frame.columns)
