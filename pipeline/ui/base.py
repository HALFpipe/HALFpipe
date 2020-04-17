# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op
import logging

from calamities import TextView, GiantTextView, SpacerView, DirectoryInputView, App
from calamities.config import config as calamities_config

from .step import Step
from .. import __version__
from ..spec import Spec, loadspec, save_spec
from ..database import Database
from ..logger import Logger

from .bids import BIDSStep
from .utils import YesNoStep


class Context:
    def __init__(self):
        self.spec = Spec()
        self.workdir = None
        self.use_existing_spec = False
        self.database = Database()
        self.smoothing_fwhm = None
        self.high_pass_filter_width = None
        self.spreadsheet_file = None
        self.debug = False

    def add_file_obj(self, file_obj):
        self.database.add_file_obj(file_obj)
        self.spec.files.append(file_obj)
        return len(self.spec.files) - 1

    def add_analysis_obj(self, analysis_obj):
        self.spec.analyses.append(analysis_obj)
        return len(self.spec.analyses) - 1


class UseExistingSpecStep(YesNoStep):
    yes_step_type = None  # continue
    no_step_type = BIDSStep

    def setup(self, ctx):
        self._append_view(TextView("Found spec file in working directory"))
        self._append_view(TextView("Use existing spec file?"))
        super(UseExistingSpecStep, self).setup(ctx)

    def next(self, ctx):
        if self.choice == "Yes":
            ctx.use_existing_spec = True
            return ctx
        return super(UseExistingSpecStep, self).next(ctx)


class WorkingDirectoryStep(Step):
    def setup(self, ctx):
        self.predefined_workdir = True
        self.is_first_run = True
        if ctx.workdir is None:
            self._append_view(TextView("Specify working directory"))
            self.workdir_input_view = DirectoryInputView(exists=False)
            self._append_view(self.workdir_input_view)
            self._append_view(SpacerView(1))
            self.predefined_workdir = False

    def run(self, ctx):
        if self.predefined_workdir:
            return self.is_first_run
        else:
            workdir = self.workdir_input_view()
            try:
                os.makedirs(workdir, exist_ok=True)
                ctx.workdir = workdir
                return True
            except Exception:
                return False

    def next(self, ctx):
        if ctx.workdir is not None and op.isdir(ctx.workdir):

            if not Logger.is_setup:
                Logger.setup(ctx.workdir, debug=ctx.debug)
        if self.is_first_run or not self.predefined_workdir:
            self.is_first_run = False
            if loadspec(ctx.workdir, logger=logging.getLogger("pipeline.ui")) is not None:
                return UseExistingSpecStep(self.app)(ctx)
            else:
                return BIDSStep(self.app)(ctx)
        else:
            return


class FirstStep(Step):
    def setup(self, ctx):
        self._append_view(GiantTextView("pipeline"))
        self._append_view(SpacerView(2))
        self._append_view(TextView("Welcome to the mindandbrain/pipeline!"))
        self._append_view(TextView(f"You are using version {__version__}"))
        self._append_view(SpacerView(1))
        self._append_view(TextView("Please report any problems or leave suggestions at"))
        self._append_view(TextView("https://github.com/mindandbrain/pipeline/issues"))
        self._append_view(SpacerView(1))
        self.is_first_run = True

    def run(self, ctx):
        return self.is_first_run

    def next(self, ctx):
        if self.is_first_run:
            self.is_first_run = False
            return WorkingDirectoryStep(self.app)(ctx)
        else:
            return


def init_spec_ui(workdir=None):
    fs_root = calamities_config.fs_root

    cur_dir = os.environ["PWD"]
    new_dir = op.join(fs_root, cur_dir[1:])
    if op.isdir(new_dir):
        os.chdir(new_dir)
    else:
        os.chdir(fs_root)

    app = App()
    ctx = Context()
    if workdir is not None:
        ctx.workdir = workdir

    with app:
        ctx = FirstStep(app)(ctx)

    if ctx is not None:
        assert ctx.workdir is not None
        workdir = ctx.workdir
        if not ctx.use_existing_spec:
            save_spec(ctx.spec, workdir=ctx.workdir, logger=logging.getLogger("pipeline.ui"))
    else:
        import sys

        logging.getLogger("pipeline.ui").info("Cancelled")
        sys.exit(0)

    return workdir
