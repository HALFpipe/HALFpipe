# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

from argparse import ArgumentParser

from multiprocessing import set_start_method

set_start_method("forkserver", force=True)

os.environ["NIPYPE_NO_ET"] = "1"  # disable nipype update check


def main():
    ap = ArgumentParser(description="mindandbrain/pipeline")
    ap.add_argument("-w", "--workdir")
    ap.add_argument("-p", "--nipype-plugin")
    ap.add_argument("-s", "--setup-only", action="store_true", default=False)
    ap.add_argument("-b", "--block-size")
    ap.add_argument("-f", "--file-status", action="store_true")
    ap.add_argument("-o", "--only-stats", action="store_true")
    ap.add_argument("-d", "--debug-nipype", action="store_true")
    ap.add_argument("-r", "--fs-root", default="/ext")
    args = ap.parse_args()

    from calamities.config import config as calamities_config

    fs_root = args.fs_root
    calamities_config.fs_root = fs_root

    cur_dir = os.environ["PWD"]
    new_dir = op.join(fs_root, cur_dir[1:])
    if op.isdir(new_dir):
        os.chdir(new_dir)
    else:
        os.chdir(fs_root)

    from calamities import App
    from .ui import Context, FirstStep

    app = App()
    ctx = Context()
    if args.workdir is not None:
        ctx.workdir = args.workdir
    with app:
        ctx = FirstStep(app)(ctx)

    from .spec import SpecSchema

    if ctx is not None:
        assert ctx.workdir is not None
        specpath = op.join(ctx.workdir, "pipeline.json")
        jsn = SpecSchema().dumps(ctx.spec, indent=4)
        with open(specpath, "w") as f:
            f.write(jsn)
