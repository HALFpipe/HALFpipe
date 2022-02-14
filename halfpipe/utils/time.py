# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

timestamp_format = "%Y-%m-%d_%H-%M"


def format_current_time() -> str:
    from datetime import datetime as dt

    return dt.now().strftime(timestamp_format)
