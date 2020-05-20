# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from calamities import (
    MultipleChoiceInputView,
    NumberInputView,
    SpacerView,
    TextView,
)

from ...spec import (
    SmoothedTagSchema,
    ConfoundsRemovedTagSchema,
    BandPassFilteredTagSchema,
)
from ..utils import YesNoStep
from ..step import Step
from .loop import AddAnotherFirstLevelAnalysisStep
from ...utils import first, ravel


class ConfirmInconsistentConfoundsSettingStep(YesNoStep):
    header_str = (
        "Do you really want to use inconsistent nuisance regressor settings across analyses?"
    )
    yes_step_type = AddAnotherFirstLevelAnalysisStep
    no_step_type = None

    def run(self, ctx):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        if self.choice == "No":
            return False
        return True


class ConfoundsSelectStep(Step):
    base_options = ["aroma_motion_[0-9]+"]
    options = {
        "Motion parameters": "(trans|rot)_[xyz]",
        "Derivatives of motion parameters": "(trans|rot)_[xyz]_derivative1",
        "Motion parameters squared": "(trans|rot)_[xyz]_power2",
        "Derivatives of motion parameters squared": "(trans|rot)_[xyz]_derivative1_power2",
        "aCompCor": "a_comp_cor_[0-9]+",
        "White matter signal": "white_matter",
        "CSF signal": "csf",
        "Global signal": "global_signal",
    }

    def setup(self, ctx):
        self._append_view(TextView("ICA-AROMA will be performed"))
        self._append_view(SpacerView(1))
        self._append_view(TextView("Remove other nuisance regressors?"))

        self.confs = set(
            analysis.tags.confounds_removed.as_tupl()
            for analysis in ctx.spec.analyses
            if analysis.tags is not None
            and analysis.tags.confounds_removed is not None
            and analysis.type != "image_output"
        )
        suggestion = []
        if len(self.confs) > 0:
            revopts = {v: k for k, v in self.options.items()}
            suggestion = [revopts[s] for s in ravel(first(self.confs))[1:] if s in revopts]
        self.input_view = MultipleChoiceInputView(
            list(self.options.keys()), checked=suggestion, isVertical=True
        )
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        valuedict = self.input_view()
        if valuedict is None:
            return False
        confoundnames = [
            self.options[name] for name, is_selected in valuedict.items() if is_selected
        ]
        confoundnames += self.base_options
        if len(confoundnames) > 0:
            ctx.spec.analyses[-1].tags.confounds_removed = ConfoundsRemovedTagSchema().load(
                {"names": confoundnames}
            )
        return True

    def next(self, ctx):
        if (
            len(self.confs) == 1
            and ctx.spec.analyses[-1].tags.confounds_removed is not None
            and ctx.spec.analyses[-1].tags.confounds_removed.as_tupl() not in self.confs
        ):
            return ConfirmInconsistentConfoundsSettingStep(self.app)(ctx)
        return AddAnotherFirstLevelAnalysisStep(self.app)(ctx)


class ConfirmInconsistentHighPassTemporalFilterSettingStep(YesNoStep):
    header_str = (
        "Do you really want to use inconsistent temporal filter width values across analyses?"
    )
    yes_step_type = ConfoundsSelectStep
    no_step_type = None

    def run(self, ctx):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        if self.choice == "No":
            return False
        return True


class HighPassTemporalFilterSettingStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Specify the temporal filter width in seconds"))
        suggestion = 125.0
        self.bptfs = set(
            analysis.tags.band_pass_filtered.as_tupl()
            for analysis in ctx.spec.analyses
            if analysis.tags is not None
            and analysis.tags.band_pass_filtered is not None
            and analysis.tags.band_pass_filtered.type == "gaussian"
            and analysis.type != "image_output"
        )
        if len(self.bptfs) > 0:
            suggestion = ravel(first(self.bptfs))[-1]
        self.input_view = NumberInputView(number=suggestion, min=0)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        value = self.input_view()
        if value is None:
            return False
        analysis_obj = ctx.spec.analyses[-1]
        analysis_obj.tags.band_pass_filtered = BandPassFilteredTagSchema().load(
            {"type": "gaussian", "high": value}
        )
        return True

    def next(self, ctx):
        if (
            len(self.bptfs) == 1
            and ctx.spec.analyses[-1].tags.band_pass_filtered.as_tupl() not in self.bptfs
        ):
            return ConfirmInconsistentHighPassTemporalFilterSettingStep(self.app)(ctx)
        return ConfoundsSelectStep(self.app)(ctx)


class DoHighPassFilterStep(YesNoStep):
    header_str = "Apply a high-pass temporal filter before feature extraction?"
    yes_step_type = HighPassTemporalFilterSettingStep
    no_step_type = ConfoundsSelectStep


class ConfirmInconsistentSmoothingSettingStep(YesNoStep):
    header_str = "Do you really want to use inconsistent smoothing FWHM values across analyses?"
    no_step_type = None

    def __init__(self, app, yes_step_type):
        self.yes_step_type = yes_step_type
        super(ConfirmInconsistentSmoothingSettingStep, self).__init__(app)

    def run(self, ctx):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        if self.choice == "No":
            return False
        return True


class PreSmoothingSettingStep(Step):
    def setup(self, ctx):
        self._append_view(TextView("Scans will be smoothed before feature extraction"))
        self._append_view(TextView("Specify the smoothing FWHM in mm"))
        suggestion = 6.0
        self.fwhms = set(
            analysis.tags.smoothed.as_tupl()
            for analysis in ctx.spec.analyses
            if analysis.tags is not None
            and analysis.tags.smoothed is not None
            and analysis.type != "image_output"
        )
        if len(self.fwhms) > 0:
            suggestion = float(first(self.fwhms)[-1])
        self.input_view = NumberInputView(number=suggestion, min=0)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self._value = self.input_view()
        if self._value is None:
            return False
        return True

    def next(self, ctx):
        assert self._value is not None
        ctx.spec.analyses[-1].tags.smoothed = SmoothedTagSchema().load({"fwhm": self._value})
        if len(self.fwhms) == 1 and ctx.spec.analyses[-1].tags.smoothed.as_tupl() not in self.fwhms:
            return ConfirmInconsistentSmoothingSettingStep(self.app, DoHighPassFilterStep)(ctx)
        return DoHighPassFilterStep(self.app)(ctx)


class ReHoAndFALFFSettingStep(Step):
    low_pass_freq = 0.1
    high_pass_freq = 0.01

    def setup(self, ctx):
        self._append_view(
            TextView(
                "Band-pass filtering is done before feature extraction "
                f"to only include the frequency band {self.high_pass_freq} - {self.low_pass_freq}Hz"
            )
        )
        self._append_view(SpacerView(1))
        self._append_view(TextView("Statistical maps will be smoothed after feature extraction"))
        self._append_view(TextView("Specify the smoothing FWHM in mm"))
        suggestion = 6.0
        self.fwhms = set(
            analysis.tags.smoothed.as_tupl()
            for analysis in ctx.spec.analyses
            if analysis.tags is not None
            and analysis.tags.smoothed is not None
            and analysis.type != "image_output"
        )
        if len(self.fwhms) > 0:
            suggestion = float(first(self.fwhms)[-1])
        self.input_view = NumberInputView(number=suggestion, min=0)
        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        value = self.input_view()
        if value is None:
            return False
        tags_obj = ctx.spec.analyses[-1].tags
        tags_obj.band_pass_filtered = BandPassFilteredTagSchema().load(
            {"type": "frequency_based", "low": self.low_pass_freq, "high": self.high_pass_freq}
        )
        tags_obj.smoothed = SmoothedTagSchema().load({"fwhm": value})
        return True

    def next(self, ctx):
        if len(self.fwhms) == 1 and ctx.spec.analyses[-1].tags.smoothed.as_tupl() not in self.fwhms:
            return ConfirmInconsistentSmoothingSettingStep(self.app, ConfoundsSelectStep)(ctx)
        return ConfoundsSelectStep(self.app)(ctx)
