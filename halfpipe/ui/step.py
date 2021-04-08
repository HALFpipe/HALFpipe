# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import abstractmethod
from typing import Optional, Type

from calamities import TextView, SpacerView, TextElement, SingleChoiceInputView

import logging
from copy import deepcopy


class Step:
    def __init__(self, app, **kwargs):
        self.app = app
        self.was_setup = False
        self.views = []
        self.kwargs = kwargs

    def __call__(self, ctx):
        try:
            if self.was_setup is False:
                self.setup(ctx)  # run only once
                self.was_setup = True
            if len(self.views) > 0:
                self.views[0].focus()  # make sure entire step is visible
            while True:
                if not self.run(ctx):
                    self.teardown()
                    return
                try:
                    new_ctx = self.next(deepcopy(ctx))
                    if new_ctx is not None:
                        return new_ctx  # only exit loop when we finish
                except Exception as e:
                    logging.getLogger("halfpipe.ui").exception("Exception: %s", e)
                    error_color = self.app.layout.color.red
                    self._append_view(TextView(TextElement(str(e), color=error_color)))
                    self._append_view(SpacerView(1))
                    if ctx.debug:
                        raise
        except Exception as e:
            self.teardown()
            raise e  # go back to previous step

    @abstractmethod
    def setup(self, ctx):
        raise NotImplementedError

    @abstractmethod
    def teardown(self):
        for view in reversed(self.views):
            logging.getLogger("halfpipe.ui").debug(f'Removing view "{view}"')
            self.app.layout.remove(view)

    @abstractmethod
    def run(self, ctx):
        raise NotImplementedError

    @abstractmethod
    def next(self, ctx):
        raise NotImplementedError

    def _append_view(self, view):
        logging.getLogger("halfpipe.ui").debug(f'Adding view "{view}"')
        view.appendto(self.app.layout)
        self.views.append(view)


StepType = Type[Step]


class BranchStep(Step):
    header_str: Optional[str] = None

    is_vertical = False

    options = dict()

    def _should_run(self, ctx):
        return True

    def setup(self, ctx):
        self.choice = None
        self.is_first_run = True

        self.should_run = self._should_run(ctx)

        if self.should_run:
            if hasattr(self, "header_str") and self.header_str is not None:
                self._append_view(TextView(self.header_str))

            self.input_view = SingleChoiceInputView(
                list(self.options.keys()), isVertical=self.is_vertical
            )

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, ctx):
        if not self.should_run:
            return self.is_first_run
        else:
            self.choice = self.input_view()
            if self.choice is None:
                return False
            return True

    def next(self, ctx):
        if self.is_first_run or self.should_run:
            self.is_first_run = False

            if self.choice is None:
                return
            elif self.options[self.choice] is None:
                return ctx
            else:
                return self.options[self.choice](self.app, **self.kwargs)(ctx)


class YesNoStep(BranchStep):
    is_vertical = False

    yes_step_type = None
    no_step_type = None

    def __init__(self, app, **kwargs):
        super(YesNoStep, self).__init__(app, **kwargs)

    @property
    def options(self):
        return {"Yes": self.yes_step_type, "No": self.no_step_type}
