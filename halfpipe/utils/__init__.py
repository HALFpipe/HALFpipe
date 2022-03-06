# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging

from inflect import engine

inflect_engine = engine()
del engine

logger = logging.getLogger("halfpipe")
del logging
