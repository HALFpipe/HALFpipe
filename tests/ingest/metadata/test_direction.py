# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from halfpipe.ingest.metadata.direction import get_axcodes_set
from halfpipe.resource import get as get_resource

from ...resource import setup as setup_test_resources


def test_get_axcodes_set():
    """
    Regression test for the `get_axcodes_set` function.
    Makes sure that bad qform information in image headers
     does not break the program. Original error was
    `ValueError: w2 should be positive, but is -9.483971e-07`
    """
    setup_test_resources()
    path = get_resource("bad_quaternion.nii.gz")
    get_axcodes_set(path)
