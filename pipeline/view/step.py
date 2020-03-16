# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from copy import deepcopy


class Step:
    def __init__(self, app):
        self.app = app
        self.was_setup = False
        self.views = []
    
    def __call__(self, ctx):
        if not self.was_setup:
            self.setup(ctx)
            self.was_setup = True
        while True:
            if not self.run(ctx):
                self.teardown()
                return False
            if self.next(deepcopy(ctx)):
                return True

    def setup(self, ctx):
        raise NotImplementedError

    def teardown(self):
        for view in self.views:
            self.app.layout.remove(view)

    def run(self, ctx):
        raise NotImplementedError

    def next(self, ctx):
        raise NotImplementedError
    
    def _append_view(self, view):
        view.appendto(self.app.layout)
        self.views.append(view)
