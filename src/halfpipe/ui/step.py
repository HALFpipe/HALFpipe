# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import abstractmethod
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import ClassVar, Dict, Optional, Type

from ..ingest.database import Database
from ..logging import logger
from ..model.spec import Spec, SpecSchema
from .components import SingleChoiceInputView, SpacerView, TextElement, TextView


class Context:
    def __init__(self) -> None:
        spec_schema = SpecSchema()
        spec = spec_schema.load(spec_schema.dump({}), partial=True)
        assert isinstance(spec, Spec)
        self.spec: Spec = spec  # initialize with defaults
        self.database = Database(self.spec)
        self.workdir: Path | None = None
        self.use_existing_spec = False
        self.debug = False
        self.already_checked: set[str] = set()

    def put(self, fileobj):
        self.database.put(fileobj)
        return len(self.spec.files) - 1


class Step:
    def __init__(self, app, **kwargs):
        self.app = app
        self.was_setup = False
        self.views = []
        self.kwargs = kwargs

    def __call__(self, ctx: Context) -> Context | None:
        try:
            if self.was_setup is False:
                self.setup(ctx)  # run only once
                self.was_setup = True
            if len(self.views) > 0:
                self.views[0].focus()  # make sure entire step is visible
            while True:
                if not self.run(ctx):
                    self.teardown()
                    return None
                try:
                    new_ctx = self.next(deepcopy(ctx))
                    if new_ctx is not None:
                        return new_ctx  # only exit loop when we finish
                except Exception as e:
                    logger.exception("Exception: %s", exc_info=e)
                    error_color = self.app.layout.color.red
                    self._append_view(TextView(TextElement(str(e), color=error_color)))
                    self._append_view(SpacerView(1))
                    if ctx.debug:
                        raise
        except Exception as e:
            self.teardown()
            raise e  # go back to previous step

    @abstractmethod
    def setup(self, ctx: Context) -> None:
        raise NotImplementedError

    def teardown(self):
        for view in reversed(self.views):
            logger.debug(f'Removing view "{view}"')
            self.app.layout.remove(view)

    @abstractmethod
    def run(self, ctx):
        raise NotImplementedError

    @abstractmethod
    def next(self, ctx):
        raise NotImplementedError

    def _append_view(self, view):
        logger.debug(f'Adding view "{view}"')
        view.appendto(self.app.layout)
        self.views.append(view)


class BranchStep(Step):
    header_str: Optional[str] = None

    is_vertical: ClassVar[bool] = False

    options: Dict[str, Optional[Type[Step]]] = defaultdict(lambda: None)

    def _should_run(self, _):
        return True

    def setup(self, ctx):
        self.choice = None
        self.is_first_run = True

        self.should_run = self._should_run(ctx)

        if self.should_run:
            if hasattr(self, "header_str") and self.header_str is not None:
                self._append_view(TextView(self.header_str))

            self.input_view = SingleChoiceInputView(list(self.options.keys()), is_vertical=self.is_vertical)

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

    def run(self, _):
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

            choice_step = self.options[self.choice]
            if choice_step is None:
                return ctx

            return choice_step(self.app, **self.kwargs)(ctx)


class YesNoStep(BranchStep):
    yes_step_type: Optional[Type[Step]] = None
    no_step_type: Optional[Type[Step]] = None

    def __init__(self, app, **kwargs):
        super(YesNoStep, self).__init__(app, **kwargs)

    @property
    def options(self):
        return {"Yes": self.yes_step_type, "No": self.no_step_type}
