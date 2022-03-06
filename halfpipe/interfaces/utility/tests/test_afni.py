# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from random import seed

import numpy as np
import pandas as pd
from nipype.interfaces import afni

from ....ingest.spreadsheet import read_spreadsheet
from ..afni import FromAFNI, ToAFNI


def test_afni(tmp_path):
    seed(a=0x5E6128C4)

    m = 100
    n = 5

    column_names = [f"column_{i+1}" for i in range(n)]

    data_frame = pd.DataFrame(np.random.rand(m, n), columns=column_names)

    data_file = tmp_path / "data.tsv"
    data_frame.to_csv(data_file, sep="\t", header=True, index=False)

    to_afni = ToAFNI(in_file=data_file)

    cwd = tmp_path / "to_afni"
    cwd.mkdir()

    result = to_afni.run(cwd=cwd)
    assert result.outputs is not None

    oned_file = result.outputs.out_file
    metadata = result.outputs.metadata

    from_afni = FromAFNI(in_file=oned_file, metadata=metadata)

    cwd = tmp_path / "from_afni"
    cwd.mkdir()

    result = from_afni.run(cwd=cwd)
    assert result.outputs is not None

    test_data_frame = read_spreadsheet(result.outputs.out_file)
    assert np.allclose(data_frame.values, test_data_frame.values)

    cwd = tmp_path / "tproject"
    cwd.mkdir()

    tproject = afni.TProject(
        in_file=oned_file,
        out_file=cwd / "filt.1D",
        bandpass=(0.01, 0.1),
        TR=2,
        polort=1,
    )

    result = tproject.run(cwd=cwd)
    assert result.outputs is not None

    from_afni = FromAFNI(in_file=result.outputs.out_file, metadata=metadata)
    result = from_afni.run(cwd=cwd)
    assert result.outputs is not None

    test_data_frame = read_spreadsheet(result.outputs.out_file)
    assert not np.allclose(data_frame.values, test_data_frame.values)
