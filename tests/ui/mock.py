# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


class MockColor:
    def __getattribute__(self, _) -> int:
        return 0


class MockLayout:
    def __init__(self, app) -> None:
        self.app = app
        self.color = MockColor()

    def append(self, view):
        view.layout = self

    def remove(self, _):
        pass

    def focus(self, _):
        pass


class MockApp:
    def __init__(self) -> None:
        self.layout = MockLayout(self)

    def dispatch(self, _):
        pass
