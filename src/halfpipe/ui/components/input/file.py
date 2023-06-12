# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
import os
from os import path as op

from ..file import get_dir, resolve
from ..keyboard import Key
from ..view import CallableView
from .choice import SingleChoiceInputView
from .text import TextInputView, common_chars


class FileInputView(CallableView):
    def __init__(self, base_path=None, exists=True, messagefun=None, **kwargs):
        super(FileInputView, self).__init__(**kwargs)
        self.text_input_view = TextInputView(
            base_path, messagefun=messagefun, forbidden_chars="'\"'", maxlen=256
        )
        self.text_input_view.update = self.update
        self.suggestion_view = SingleChoiceInputView(
            [], isVertical=True, addBrackets=False
        )
        self.suggestion_view.update = self.update

        self.matching_files = []
        self.cur_dir = None
        self.cur_dir_files = []
        self.exists = exists

    @property
    def text(self):
        return self.text_input_view.text

    @text.setter
    def text(self, val):
        self.text_input_view.text = val

    def setup(self):
        super(FileInputView, self).setup()
        self.text_input_view.layout = self.layout
        self.text_input_view.setup()
        self.suggestion_view.layout = self.layout
        self.suggestion_view.setup()

    def _before_call(self):
        self.text_input_view._before_call()
        self.text_input_view.isActive = True
        self._scan_files()

    def _is_ok(self):
        if self.exists:
            try:
                path = str(self.text).strip()
                return op.isfile(resolve(path))
            except Exception:
                return False
        return True

    def _getOutput(self):
        if self.text is not None:
            try:
                path = str(self.text).strip()
                return resolve(path)
            except Exception:
                pass

    def _scan_dir(self):
        path = str(self.text).strip()
        dir = get_dir(path)
        if dir != self.cur_dir:
            self.cur_dir = dir
            self.cur_dir_files = []

            try:
                real_dir = resolve(self.cur_dir)
                with os.scandir(real_dir) as it:
                    for entry in it:
                        try:
                            filepath = entry.name
                            if filepath[0] == ".":
                                continue
                            if entry.is_dir():
                                filepath += "/"
                            self.cur_dir_files.append(filepath)
                        except OSError:
                            pass
            except OSError:
                pass

    def _scan_files(self):
        if self.text is None:
            return

        self._scan_dir()

        new_matching_files = []
        basename = op.basename(self.text)
        for entry in self.cur_dir_files:
            if entry.startswith(basename):
                new_matching_files.append(entry)
        new_matching_files.sort()
        self.matching_files = new_matching_files
        self.suggestion_view.set_options(self.matching_files)

    def _handleKey(self, c):
        if c == Key.Break:
            self.text = None
            self.suggestion_view.set_options([])
            self.isActive = False
        elif (
            self.suggestion_view.isActive and self.suggestion_view.cur_index is not None
        ):
            if c == Key.Up and self.suggestion_view.cur_index == 0:
                self.suggestion_view.offset = 0
                self.suggestion_view.cur_index = None
                self.suggestion_view.isActive = False
                self.text_input_view.isActive = True
                self.text_input_view._before_call()
                self.update()
            elif c == Key.Return or c == Key.Right:
                self.text = op.join(
                    op.dirname(str(self.text)), str(self.suggestion_view._getOutput())
                )
                self._scan_files()
                self.suggestion_view.cur_index = None
                self.suggestion_view.isActive = False
                self.text_input_view.isActive = True
                self.text_input_view.cur_index = len(self.text)
                self.text_input_view._before_call()
                self.update()
            elif c == Key.Left:
                self.text = op.dirname(str(self.text))
                self._scan_files()
                self.update()
            else:
                self.suggestion_view._handleKey(c)
        else:
            cur_text = self.text
            if c == Key.Down and len(self.matching_files) > 0:
                self.suggestion_view.isActive = True
                self.text_input_view.isActive = False
                self.suggestion_view._before_call()
                self.update()
            elif c == Key.Tab and len(self.matching_files) > 0:
                cc = common_chars(self.matching_files)
                self.text = op.join(op.dirname(str(self.text)), cc)
                self.text_input_view.cur_index = len(self.text)
            elif c == Key.Return:
                if self._is_ok():
                    self.suggestion_view.set_options([])
                    self.suggestion_view.isActive = False
                    self.text_input_view.isActive = False
                    self.isActive = False
            else:
                if not self.text_input_view.isActive:
                    self.suggestion_view.isActive = False
                    self.text_input_view.isActive = True
                    self.text_input_view._before_call()
                    self.update()
                self.text_input_view._handleKey(c)

            if self.text is not None and self.text != cur_text:
                # was changed
                self._scan_files()
                self.update()

    def drawAt(self, y):
        if y is None:
            return
        size = 0
        size += self.text_input_view.drawAt(y + size)
        size += self.suggestion_view.drawAt(y + size)

        if self.text_input_view._viewWidth > self._viewWidth:
            self._viewWidth = self.text_input_view._viewWidth
        if self.suggestion_view._viewWidth > self._viewWidth:
            self._viewWidth = self.suggestion_view._viewWidth

        return size


class DirectoryInputView(FileInputView):
    def _is_ok(self):
        if self.exists:
            try:
                path = str(self.text).strip()
                return op.isdir(resolve(path))
            except Exception:
                return False
        return True

    def _scan_dir(self):
        path = str(self.text).strip()
        dir = get_dir(path)
        if dir != self.cur_dir:
            self.cur_dir = dir
            self.cur_dir_files = []

            try:
                real_dir = resolve(self.cur_dir)
                with os.scandir(real_dir) as it:
                    for entry in it:
                        try:
                            filepath = entry.name
                            if filepath[0] == ".":
                                continue
                            if entry.is_dir():
                                filepath += "/"
                                self.cur_dir_files.append(filepath)
                        except OSError:
                            pass
            except OSError:
                pass
