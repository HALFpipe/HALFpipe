# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

try:
    import curses

    curses.setupterm()  # noqa
except Exception:
    pass

from .app import App
from .keyboard import Key, Keyboard
from .view import View, TextView, GiantTextView, SpacerView
from .input import (
    TextInputView,
    NumberInputView,
    MultiTextInputView,
    MultiNumberInputView,
    SingleChoiceInputView,
    MultipleChoiceInputView,
    MultiSingleChoiceInputView,
    MultiMultipleChoiceInputView,
    MultiCombinedTextAndSingleChoiceInputView,
    CombinedMultipleAndSingleChoiceInputView,
    MultiCombinedNumberAndSingleChoiceInputView,
    FileInputView,
    DirectoryInputView,
    FilePatternInputView,
)
from .layout import Layout
from .text import Text, TextElement, TextElementCollection

__all__ = [
    App,
    Key,
    Keyboard,
    View,
    TextView,
    GiantTextView,
    SpacerView,
    TextInputView,
    NumberInputView,
    MultiTextInputView,
    MultiNumberInputView,
    SingleChoiceInputView,
    MultipleChoiceInputView,
    MultiSingleChoiceInputView,
    MultiMultipleChoiceInputView,
    CombinedMultipleAndSingleChoiceInputView,
    MultiCombinedTextAndSingleChoiceInputView,
    MultiCombinedNumberAndSingleChoiceInputView,
    FileInputView,
    DirectoryInputView,
    FilePatternInputView,
    Layout,
    Text,
    TextElement,
    TextElementCollection,
]
