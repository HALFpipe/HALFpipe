# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from calamities import TextView, DirectoryInputView, SpacerView

from ..step import Step, YesNoStep
from .anat import AnatSummaryStep, AnatStep
from ...model import BidsFileSchema


class GetBidsDirStep(Step):
    def _message(self):
        return self.message

    def setup(self, ctx):
        self._append_view(TextView("Specify the path of the BIDS directory"))
        self.message = None
        self.bids_dir_input_view = DirectoryInputView(messagefun=self._message)
        self._append_view(self.bids_dir_input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        bids_dir = self.bids_dir_input_view()
        if bids_dir is None:
            return False

    def next(self, ctx):
        ctx.put(BidsFileSchema().load({"datatype": "bids", "path": self.bids_dir}))

        return AnatSummaryStep(self.app)(ctx)


class IsBidsStep(YesNoStep):
    header_str = "Is the data available in BIDS format?"
    yes_step_type = GetBidsDirStep
    no_step_type = AnatStep


BidsStep = IsBidsStep
