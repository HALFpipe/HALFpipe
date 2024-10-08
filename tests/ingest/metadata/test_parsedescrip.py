# -*- coding: utf-8 -*-

import nibabel as nib
import pytest

from halfpipe.ingest.metadata.niftiheader import parse_descrip  # noqa


@pytest.mark.parametrize(
    "test_descrip, expected_dict",
    [
        (
            "te=0.3;tr=1",
            {"echo_time": 0.3, "repetition_time": 1.0},
        ),  # case1 both s; te < 1 & tr <= 100
        (
            "te=300;tr=200",
            {"echo_time": 0.3, "repetition_time": 0.2},
        ),  # case2 both ms; te >=1 & tr > 100
        (
            "te=0.3;tr=1000",
            {"echo_time": 0.3, "repetition_time": 1.0},
        ),  # case3 te/s tr/ms; te < 1 & tr > 100
        (
            "te=300;tr=1",
            {"echo_time": 0.3, "repetition_time": 1.0},
        ),  # case4 te/ms tr/s; te >=1 & tr <= 100
        ("te=0.3", {"echo_time": 0.3}),  # case5 te/specified tr/none;
        ("tr=1", {"repetition_time": 1.0}),  # case6 te/None tr/specified;
        ("", {}),  # case7 both None;
    ],
)
def test_parse_descrip(tmp_path, test_descrip, expected_dict):
    header = nib.nifti1.Nifti1Header()
    header["descrip"] = test_descrip

    descrip_dict = parse_descrip(header=header)
    assert descrip_dict == expected_dict
