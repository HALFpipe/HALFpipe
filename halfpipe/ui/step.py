# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from calamities import TextView, SpacerView, TextElement

import logging
from copy import deepcopy


class Step:
    def __init__(self, app):
        self.app = app
        self.was_setup = False
        self.views = []

    def __call__(self, ctx):
        try:
            if not self.was_setup:
                self.setup(ctx)
                self.was_setup = True
            while True:
                if not self.run(ctx):
                    self.teardown()
                    return
                try:
                    new_ctx = self.next(deepcopy(ctx))
                    if new_ctx is not None:
                        return new_ctx
                except Exception as e:
                    logging.getLogger("halfpipe.ui").exception("Exception: %s", e)
                    error_color = self.app.layout.color.red
                    self._append_view(TextView(TextElement(str(e), color=error_color)))
                    self._append_view(SpacerView(1))
        except Exception as e:
            self.teardown()
            raise e  # go back to previous step

    def setup(self, ctx):
        raise NotImplementedError

    def teardown(self):
        for view in reversed(self.views):
            self.app.layout.remove(view)

    def run(self, ctx):
        raise NotImplementedError

    def next(self, ctx):
        raise NotImplementedError

    def _append_view(self, view):
        view.appendto(self.app.layout)
        self.views.append(view)
