# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pipeline.fmriprepconfig import config as fmriprepconfig
from templateflow import api

assert len(api.get(fmriprepconfig.skull_strip_template.space)) > 0
assert all(len(api.get(space)) > 0 for space in fmriprepconfig.spaces.get_spaces())
