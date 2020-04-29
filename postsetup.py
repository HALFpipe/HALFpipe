# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pkg_resources
from fmriprep import config
from templateflow import api

from pipeline.resources import ONLINE_RESOURCES, get

configfilename = pkg_resources.resource_filename("pipeline", "data/config.toml")
config.load(configfilename)

assert len(api.get(config.workflow.skull_strip_template)) > 0
assert all(
    len(api.get(space, atlas=None)) > 0 for space in config.workflow.spaces.get_spaces()
)
extra_spaces = ["MNI152NLin6Asym"]
assert all(len(api.get(space, atlas=None)) > 0 for space in extra_spaces)

for filename in ONLINE_RESOURCES.keys():
    get(filename)
