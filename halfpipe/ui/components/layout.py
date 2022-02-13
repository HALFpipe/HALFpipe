# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import curses

base_pad_width = 1024


class Layout:
    def __init__(self, app):
        self.app = app
        self.color = app.color
        self.keyboard = app.keyboard

        self.viewsById = {}
        self.viewOrder = []
        self.viewSizesById = {}
        self.focusedView = None

        self.viewportMin = 0

        self.window = curses.newpad(16384, base_pad_width)
        self.window.leaveok(False)

        self.statusBar = curses.newpad(1, base_pad_width)
        self.statusBar.bkgd(" ", self.color.white)

        self.draw()

    def append(self, view):
        id = view.id
        self.viewsById[id] = view
        self.viewSizesById[id] = 0
        self.viewOrder.append(id)
        view.layout = self
        self.focusedView = view
        return view  # for chaining

    def remove(self, view):
        view.erase()
        id = view.id
        if id in self.viewsById:
            del self.viewsById[id]
        if id in self.viewSizesById:
            del self.viewSizesById[id]
        try:
            self.viewOrder.remove(id)
        except ValueError:
            pass
        if self.focusedView == view:
            self.focusedView = None
        return view  # for chaining

    def focus(self, view):
        self.focusedView = view

    def _calc_viewport(self, viewportSize):
        if self.focusedView is None:
            return

        viewSize = self.getViewSize(self.focusedView)
        viewMin = self.offset(self.focusedView)
        if viewSize is None or viewMin is None:
            return
        if viewMin < self.viewportMin:
            self.viewportMin = viewMin
            return
        viewMax = viewMin + viewSize
        viewportMax = self.viewportMin + viewportSize
        if viewMax > viewportMax:
            self.viewportMin += viewMax - viewportMax

    def getLayoutSize(self):
        y, x = self.app.screen.getmaxyx()
        return (y - 1, x - 1)

    def draw(self):
        y, x = self.getLayoutSize()
        self._calc_viewport(y - 1)
        self.window.noutrefresh(self.viewportMin, 0, 0, 0, y - 2, x)
        try:
            self.statusBar.noutrefresh(0, 0, y, 0, y, x)
        except Exception:
            pass
        curses.doupdate()

    def getViewSize(self, view):
        if view.id in self.viewSizesById:
            return self.viewSizesById[view.id]

    def setViewSize(self, view, newSize):
        if view.id not in self.viewSizesById or newSize is None:
            return
        if self.viewSizesById[view.id] != newSize:
            self.viewSizesById[view.id] = newSize
            index = self.viewOrder.index(view.id)
            for dependentViewId in self.viewOrder[index + 1 :]:
                self.viewsById[dependentViewId].draw()

    def offset(self, view):
        try:
            index = self.viewOrder.index(view.id)
            return sum([self.viewSizesById[id] for id in self.viewOrder[:index]])
        except ValueError:
            return

    def clearStatusBar(self):
        self.statusBar.erase()

    def setStatusBar(self, text):
        self.clearStatusBar()
        self.statusBar.addstr(0, 0, text, self.color.white)
