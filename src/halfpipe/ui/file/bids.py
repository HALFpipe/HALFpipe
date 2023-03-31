# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ...model.file.bids import BidsFileSchema
from ..components import DirectoryInputView, SpacerView, TextView
from ..step import Step, YesNoStep
from .anat import AnatStep, AnatSummaryStep


class GetBidsDirStep(Step):
    def _message(self):
        return self.message

    def setup(self, ctx):
        self.bids_dir = None

        self._append_view(TextView("Specify the path of the BIDS directory"))

        self.message = None
        self.input_view = DirectoryInputView(messagefun=self._message)
        self._append_view(self.input_view)

        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.bids_dir = self.input_view()
        if self.bids_dir is None:
            return False
        return True

    def next(self, ctx):
        ctx.put(BidsFileSchema().load({"datatype": "bids", "path": self.bids_dir}))

        return AnatSummaryStep(self.app)(ctx)


class IsBidsStep(YesNoStep):
    header_str = "Is the data available in BIDS format?"
    yes_step_type = GetBidsDirStep
    no_step_type = AnatStep


BidsStep = IsBidsStep
