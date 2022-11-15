# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging

from .base import setup, teardown
from .context import context as logging_context

logger = logging.getLogger("halfpipe")
del logging

__all__ = ["setup", "teardown", "logger", "logging_context"]
