# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nibabel as nib


def get_repetition_time(fname):
    try:
        nbimg = nib.load(fname)
        return float(nbimg.header.get_zooms()[3])
    except Exception:
        return
