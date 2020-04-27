# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nibabel as nib

from ..utils import nvol


def get_repetition_time(fname):
    try:
        nbimg = nib.load(fname)
        assert nvol(nbimg) > 1, "Cannot get repetition time for single volume"
        repetition_time = float(nbimg.header.get_zooms()[3])
        return repetition_time
    except Exception:
        return
