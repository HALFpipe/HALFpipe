# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op
from pathlib import Path
import logging

from calamities import (
    TextView,
    GiantTextView,
    SpacerView,
    DirectoryInputView,
    App,
    SingleChoiceInputView,
)
from calamities.config import config as calamities_config

from .step import Step
from .. import __version__
from ..model import SpecSchema, loadspec, savespec
from ..io import Database
from ..logger import Logger

from .file import BidsStep
from .feature import FeaturesStep
from .model import ModelsStep


class Context:
    def __init__(self):
        spec_schema = SpecSchema()
        self.spec = spec_schema.load(spec_schema.dump({}), partial=True)  # initialize with defaults
        self.database = Database(self.spec)

        self.workdir = None
        self.use_existing_spec = False
        self.debug = False

        self.already_checked = set()

    def put(self, fileobj):
        self.database.put(fileobj)
        return len(self.spec.files) - 1


class UseExistingSpecStep(Step):
    options = [
        "Run without modification",
        "Start over at beginning",
        "Start over at features",
        "Start over at models",
        "Add another model",
    ]

    def setup(self, ctx):
        self.is_first_run = True
        self.existing_spec = loadspec(ctx.workdir, logger=logging.getLogger("halfpipe.ui"))
        self.choice = None
        if self.existing_spec is not None:
            self._append_view(TextView("Found spec file in working directory"))

            options = self.options[:3]

            if len(self.existing_spec.features) > 0:
                options.append(self.options[3])
            if len(self.existing_spec.models) > 0:
                options.append(self.options[4])

            self.input_view = SingleChoiceInputView(options, isVertical=True)
            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if self.existing_spec is not None:
            self.choice = self.input_view()
            if self.choice is None:
                return False
            return True
        else:
            return self.is_first_run

    def next(self, ctx):
        if self.is_first_run or self.existing_spec is not None:
            self.is_first_run = False

            if self.choice is None:
                return BidsStep(self.app)(ctx)

            choice_index = self.options.index(self.choice)

            files = self.existing_spec.files
            settings = self.existing_spec.settings
            features = self.existing_spec.features
            models = self.existing_spec.models

            if choice_index > 1:
                for fileobj in files:
                    ctx.put(fileobj)
            if choice_index > 2:
                ctx.spec.settings = settings
                ctx.spec.features = features

            if choice_index == 0:
                ctx.use_existing_spec = True
                return ctx
            elif choice_index == 1:
                return BidsStep(self.app)(ctx)
            elif choice_index == 2:
                return FeaturesStep(self.app)(ctx)
            elif choice_index > 2:
                if choice_index == 4:
                    ctx.spec.models = models
                return ModelsStep(self.app)(ctx)
        else:
            return


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
            return UseExistingSpecStep(self.app)(ctx)
        else:
            return


class FirstStep(Step):
    def setup(self, ctx):
        self._append_view(GiantTextView("Halfpipe"))
        self._append_view(SpacerView(2))
        self._append_view(TextView("Welcome to ENIGMA Halfpipe!"))
        self._append_view(TextView(f"You are using version {__version__}"))
        self._append_view(SpacerView(1))
        self._append_view(TextView("Please report any problems or leave suggestions at"))
        self._append_view(TextView("https://github.com/mindandbrain/halfpipe/issues"))
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


def init_spec_ui(workdir=None, debug=False):
    fs_root = calamities_config.fs_root

    cur_dir = str(Path.cwd())
    new_dir = op.join(fs_root, cur_dir[1:])
    if op.isdir(new_dir):
        os.chdir(new_dir)
    else:
        os.chdir(fs_root)

    app = App()
    ctx = Context()
    ctx.debug = debug
    if workdir is not None:
        ctx.workdir = workdir

    with app:
        ctx = FirstStep(app)(ctx)

    if ctx is not None:
        assert ctx.workdir is not None
        workdir = ctx.workdir
        if not ctx.use_existing_spec:
            savespec(ctx.spec, workdir=ctx.workdir, logger=logging.getLogger("halfpipe.ui"))
    else:
        import sys

        logging.getLogger("halfpipe.ui").info("Cancelled")
        sys.exit(0)

    return workdir
