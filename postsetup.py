# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from templateflow import api

from halfpipe.resources import ONLINE_RESOURCES, get

spaces = ["MNI152NLin6Asym", "MNI152NLin2009cAsym"]
assert all(len(api.get(space, atlas=None)) > 0 for space in spaces)

for filename in ONLINE_RESOURCES.keys():
    get(filename)
