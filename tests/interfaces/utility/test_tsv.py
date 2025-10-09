import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from halfpipe.interfaces.utility.tsv import FillNA


def test_fillna(tmp_path: Path) -> None:
    os.chdir(str(tmp_path))

    data = pd.DataFrame(
        dict(
            a=[1.0, 2.0, np.nan, 4.0],
            b=[np.nan, 2.0, 3.0, 4.0],
            c=[1.0, np.nan, 3.0, np.nan],
        )
    )
    tsv_path = "test.tsv"
    data.to_csv(tsv_path, sep="\t", index=False, na_rep="n/a")

    fillna = FillNA(in_tsv=str(tsv_path))
    result = fillna.run()
    outputs = result.outputs

    out_with_header = outputs.out_with_header
    pd.testing.assert_frame_equal(
        pd.read_csv(out_with_header, sep="\t"),
        data.fillna(0.0),
    )

    out_no_header = outputs.out_no_header
    np.testing.assert_allclose(
        np.nan_to_num(data.to_numpy()),
        np.loadtxt(out_no_header),
    )


def test_fillna_empty(tmp_path: Path) -> None:
    os.chdir(str(tmp_path))

    tsv_path = "test.tsv"
    pd.DataFrame().to_csv(tsv_path, sep="\t", index=False, na_rep="n/a")

    fillna = FillNA(in_tsv=str(tsv_path))
    result = fillna.run()
    outputs = result.outputs

    out_no_header = outputs.out_no_header

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        np.testing.assert_allclose(
            np.array([]),
            np.loadtxt(out_no_header),
        )
