# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ...resource import get as getresource
from ...tests.resource import setup as setuptestresources
from ..condition import parse_condition_file

txt_str = """8 32 1
72 32 1
136 32 1
200 32 1
"""

tsv_str = """onset duration  trial_type  response_time stim_file
1.2 0.6 go  1.435 images/red_square.jpg
5.6 0.6 stop  1.739 images/blue_square.jpg
"""


def test_parse_condition_file_txt(tmp_path):
    file_name = tmp_path / "faces.txt"

    with open(file_name, "w") as fp:
        fp.write(txt_str)

    conditions, onsets, durations = parse_condition_file(
        in_any=((file_name, "faces"), (file_name, "shapes"))
    )

    assert all(v == 32 for d in durations for v in d)
    assert all(v[0] == 8 for v in onsets)
    assert tuple(conditions) == ("faces", "shapes")


def test_parse_condition_file_tsv(tmp_path):
    file_name = tmp_path / "gonogo.tsv"

    with open(file_name, "w") as fp:
        fp.write(tsv_str)

    conditions, onsets, durations = parse_condition_file(in_any=file_name)

    assert tuple(conditions) == ("go", "stop")
    assert all(len(v) > 0 for v in durations)
    assert all(len(v) > 0 for v in onsets)


def test_parse_condition_file_mat():
    setuptestresources()
    file_name = getresource("run_01_spmdef.mat")

    conditions, onsets, durations = parse_condition_file(in_any=file_name)

    assert tuple(conditions) == ("Famous", "Unfamiliar", "Scrambled")
    assert all(len(v) > 0 for v in durations)
    assert all(len(v) > 0 for v in onsets)
