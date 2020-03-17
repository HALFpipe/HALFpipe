# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

from . import __version__

from multiprocessing import set_start_method, cpu_count
set_start_method("forkserver", force=True)

os.environ["NIPYPE_NO_ET"] = "1"  # disable nipype update check

def main():
    from calamities.config import config as calamities_config
    fs_root = "/ext"
    calamities_config.fs_root = fs_root
    
    cur_dir = os.environ["PWD"]
    os.chdir(op.join(fs_root, cur_dir[1:]))
    
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
