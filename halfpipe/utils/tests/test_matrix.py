# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..matrix import load_vector


def test_load_vector(tmp_path):
    test_data = "1,2,3,4,5,7,9,10,11,13,14"
    test_file_path = tmp_path / "test.txt"

    with open(test_file_path, "w") as test_file_handle:
        test_file_handle.write(test_data)
        test_file_handle.write("\n")

    a = [int(x) for x in test_data.split(",")]
    b = load_vector(test_file_path)

    assert tuple(a) == tuple(b)
