# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""


timestampfmt = "%Y-%m-%d_%H-%M"


def timestampstr() -> str:
    from datetime import datetime as dt

    return dt.now().strftime(timestampfmt)
