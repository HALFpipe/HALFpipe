# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

try:
    import curses

    curses.setupterm()  # noqa
except Exception:
    pass

from .app import App
from .input import (
    CombinedMultipleAndSingleChoiceInputView,
    DirectoryInputView,
    FileInputView,
    FilePatternInputView,
    MultiCombinedNumberAndSingleChoiceInputView,
    MultiCombinedTextAndSingleChoiceInputView,
    MultiMultipleChoiceInputView,
    MultiNumberInputView,
    MultipleChoiceInputView,
    MultiSingleChoiceInputView,
    MultiTextInputView,
    NumberInputView,
    SingleChoiceInputView,
    TextInputView,
)
from .keyboard import Key, Keyboard
from .layout import Layout
from .text import Text, TextElement, TextElementCollection
from .view import GiantTextView, SpacerView, TextView, View

__all__ = [
    "App",
    "Key",
    "Keyboard",
    "View",
    "TextView",
    "GiantTextView",
    "SpacerView",
    "TextInputView",
    "NumberInputView",
    "MultiTextInputView",
    "MultiNumberInputView",
    "SingleChoiceInputView",
    "MultipleChoiceInputView",
    "MultiSingleChoiceInputView",
    "MultiMultipleChoiceInputView",
    "CombinedMultipleAndSingleChoiceInputView",
    "MultiCombinedTextAndSingleChoiceInputView",
    "MultiCombinedNumberAndSingleChoiceInputView",
    "FileInputView",
    "DirectoryInputView",
    "FilePatternInputView",
    "Layout",
    "Text",
    "TextElement",
    "TextElementCollection",
]
