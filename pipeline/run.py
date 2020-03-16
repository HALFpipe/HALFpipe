# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os

from . import __version__

from multiprocessing import set_start_method, cpu_count
set_start_method("forkserver", force=True)

os.environ["NIPYPE_NO_ET"] = "1"  # disable nipype update check

EXT_PATH = "/ext"


def main():
    from calamities import (
        App
    )
    from .view import (
        Context,
        FirstStep
    )
    app = App()
    ctx = Context()
    with app:
        FirstStep(app)(ctx)
