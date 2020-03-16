# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from calamities import (
    App,
    TextView,
    TextInputView,
    SingleChoiceInputView,
    MultipleChoiceInputView,
    MultiSingleChoiceInputView,
    MultiMultipleChoiceInputView,
    GiantTextView,
    SpacerView,
    FileInputView,
    DirectoryInputView,
    FilePatternInputView
)

from .step import Step
from .. import __version__


class Context:
    def __init__(self):
        pass


class FirstStep(Step):
    def setup(self, ctx):
        self._append_view(GiantTextView("pipeline"))
        self._append_view(SpacerView(2))
        self._append_view(TextView("Welcome to the mindandbrain/pipeline!"))
        self._append_view(TextView(f"You are using version {__version__}"))
        self._append_view(SpacerView(1))
        self._append_view(TextView("Please report any problems or leave suggestions at"))
        self._append_view(TextView("https://github.com/mindandbrain/pipeline/issues"))
        self._append_view(SpacerView(1))
        self.is_first_run = True

    def run(self, ctx):
        if not self.is_first_run:
            return False
        self.is_first_run = False
        return True

    def next(self, ctx):
        return IsBIDSStep(self.app)(ctx)


class IsBIDSStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Is the data available in BIDS format?"))
        self.yes_no_input_view = SingleChoiceInputView(["Yes", "No"], cur_index=1)
        self._append_view(self.yes_no_input_view)
        self._append_view(SpacerView(1))
        self.is_bids = None
    
    def run(self, ctx):
        choice = self.yes_no_input_view()
        if choice is None:
            return False
        self.is_bids = "Yes" in choice
        return True

    def next(self, ctx):
        if self.is_bids:
            return GetBIDSDirStep(self.app)(ctx)
        else:
            return AnatStep(self.app)(ctx)
            

class GetBIDSDirStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify BIDS directory"))
        self.bids_dir_input_view = DirectoryInputView()
        self._append_view(self.bids_dir_input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        bids_dir = self.bids_dir_input_view()
        if bids_dir is None:
            return False
        # TODO
        return True

    def next(self, ctx):
        return True


class AnatStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Please specify anatomical/structural data"))
        self._append_view(TextView("Specify the path of the T1-weighted image files"))
        entity_instruction = TextView("")
        self._append_view(entity_instruction)
        self.anat_pattern_input_view = FilePatternInputView(["subject"])
        self._append_view(self.anat_pattern_input_view)
        entity_instruction.text = self.anat_pattern_input_view._tokenize(
            "Specify {subject} in place of the subject names"
        )
        self._append_view(SpacerView(1))

    def run(self, ctx):
        pattern = self.anat_pattern_input_view()
        if pattern is None:
            return False
        # TODO
        return True

    def next(self, ctx):
        return True
    
    