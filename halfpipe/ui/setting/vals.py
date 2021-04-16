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
    MultiCombinedNumberAndSingleChoiceInputView
)

from collections import OrderedDict
from more_itertools import unique_everseen

from ..step import Step, BranchStep, YesNoStep
from ...model import (
    SmoothingSettingSchema,
    BandpassFilterSettingSchema,
    GrandMeanScalingSettingSchema,
)
from ...utils import inflect_engine as p


def get_setting_vals_steps(next_step_type, noun="setting", vals_header_str=None, oncompletefn=None):
    class ConfirmInconsistentStep(YesNoStep):
        no_step_type = None

        def __init__(self, app, val_noun, this_next_step_type):
            self.header_str = f"Do you really want to use inconsistent {val_noun} across {p.plural(noun)}?"
            self.yes_step_type = this_next_step_type
            super(ConfirmInconsistentStep, self).__init__(app)

        def run(self, ctx):
            self.choice = self.input_view()
            if self.choice is None:
                return False
            if self.choice == "No":
                return False
            return True

    class ConfoundsSelectStep(Step):
        noun = "confounds"

        options = {
            "ICA-AROMA": "ICA-AROMA",
            "Motion parameters": "(trans|rot)_[xyz]",
            "Derivatives of motion parameters": "(trans|rot)_[xyz]_derivative1",
            "Motion parameters squared": "(trans|rot)_[xyz]_power2",
            "Derivatives of motion parameters squared": "(trans|rot)_[xyz]_derivative1_power2",
            "aCompCor (top five components)": "a_comp_cor_0[0-4]",
            "White matter signal": "white_matter",
            "CSF signal": "csf",
            "Global signal": "global_signal",
        }

        def setup(self, ctx):
            self._append_view(TextView(f"Remove {self.noun}?"))

            featuresettings = set(
                feature.setting for feature in ctx.spec.features if hasattr(feature, "setting")
            )

            self.confs = list(unique_everseen(
                frozenset(
                    setting.get("confounds_removal", [])
                    + (
                        ["ICA-AROMA"]
                        if setting.get("ica_aroma") is True
                        else []
                    )
                )
                for setting in ctx.spec.settings[:-1]
                # only include active settings
                if setting.get("output_image", False) or setting["name"] in featuresettings
            ))

            suggestion = ["ICA-AROMA"]

            if len(self.confs) > 0:
                inverse_options = {v: k for k, v in self.options.items()}
                suggestion = [inverse_options[s] for s in self.confs[-1] if s in inverse_options]

            self.input_view = MultipleChoiceInputView(
                list(self.options.keys()), checked=suggestion, isVertical=True
            )

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

            self.valuedict = None

        def run(self, ctx):
            self.valuedict = self.input_view()
            if self.valuedict is None:
                return False
            return True

        def next(self, ctx):
            confoundnames = [
                self.options[name] for name, is_selected in self.valuedict.items() if is_selected
            ]

            ica_aroma = "ICA-AROMA" in confoundnames
            ctx.spec.settings[-1]["ica_aroma"] = ica_aroma

            settingconfoundnames = [name for name in confoundnames if name != "ICA-AROMA"]
            if len(settingconfoundnames) > 0:
                ctx.spec.settings[-1]["confounds_removal"] = settingconfoundnames

            if oncompletefn is not None:
                oncompletefn(ctx)

            this_next_step_type = next_step_type

            if (
                len(self.confs) == 1
                and len(confoundnames) > 0
                and frozenset(confoundnames) not in self.confs
            ):
                return ConfirmInconsistentStep(self.app, self.noun, this_next_step_type)(ctx)

            return this_next_step_type(self.app)(ctx)

    class FrequencyBasedBandpassSettingStep(Step):
        noun = "filter cutoff frequencies"
        unit = "Hz"

        keys = ["low", "high"]
        display_strs = ["Low cutoff", "High cutoff"]

        type_str = "frequency_based"
        suggestion = (0.01, 0.1)

        def setup(self, ctx):
            self._append_view(TextView(f"Specify the {self.noun} in {self.unit}"))

            suggestion = [*self.suggestion]

            featuresettings = set(
                feature.setting for feature in ctx.spec.features if hasattr(feature, "setting")
            )

            self.valsets = OrderedDict()

            for i, key in enumerate(self.keys):
                self.valsets[key] = list()
                valset = self.valsets[key]

                for setting in ctx.spec.settings:
                    if not setting.get("output_image", False) and setting["name"] not in featuresettings:
                        continue

                    bandpass_filter = setting.get("bandpass_filter")
                    if bandpass_filter is not None and key in bandpass_filter:
                        valset.append(bandpass_filter[key])

                valset = list(unique_everseen(valset))

                if len(valset) > 0:
                    suggestion[i] = valset[-1]

            self.input_view = MultiCombinedNumberAndSingleChoiceInputView(
                self.display_strs, ["Skip"], initial_values=suggestion
            )

            self._append_view(self.input_view)
            self._append_view(SpacerView(1))

            self.value = None

        def run(self, ctx):
            self.value = self.input_view()
            if self.value is None:
                return False
            return True

        def next(self, ctx):
            filterdict = {"type": self.type_str}
            for key, display_str in zip(self.keys, self.display_strs):
                display_str = str(display_str)
                if self.value.get(display_str) is not None:
                    if isinstance(self.value[display_str], float):
                        filterdict[key] = self.value[display_str]
                    elif self.value[display_str] == "Skip":
                        pass
                    else:
                        raise ValueError(
                            f'Unknown bandpass filter value "{self.value[display_str]}"'
                        )

            if len(filterdict) > 1:
                ctx.spec.settings[-1]["bandpass_filter"] = BandpassFilterSettingSchema().load(
                    filterdict
                )

            this_next_step_type = ConfoundsSelectStep

            if any(
                len(self.valsets[key]) == 1 and filterdict[key] not in self.valsets[key]
                for key in self.keys
            ):
                return ConfirmInconsistentStep(self.app, f"{self.noun} values", this_next_step_type)(ctx)

            return this_next_step_type(self.app)(ctx)

    class GaussianWeightedBandpassSettingStep(FrequencyBasedBandpassSettingStep):
        noun = "filter width"
        unit = "seconds"

        keys = ["lp_width", "hp_width"]
        display_strs = ["Low-pass width", "High-pass width"]

        type_str = "gaussian"
        suggestion = ("Skip", 125.0)

    class BandpassFilterTypeStep(BranchStep):
        is_vertical = True
        header_str = "Specify the type of temporal filter"
        options = {
            "Gaussian-weighted": GaussianWeightedBandpassSettingStep,
            "Frequency-based": FrequencyBasedBandpassSettingStep,
        }

    class DoBandpassFilterStep(YesNoStep):
        header_str = "Apply a temporal filter?"

        yes_step_type = BandpassFilterTypeStep
        no_step_type = ConfoundsSelectStep

        def _should_run(self, ctx):
            if "bandpass_filter" not in ctx.spec.settings[-1]:
                return True

            bandpass_filter = ctx.spec.settings[-1]["bandpass_filter"]

            self.choice = "Yes"

            type = bandpass_filter.get("type")
            if type == "gaussian":
                self.yes_step_type = GaussianWeightedBandpassSettingStep

                message = "Temporal filtering will be applied using a gaussian-weighted filter"
                self._append_view(TextView(message))

                lp_sigma, hp_sigma = (
                    bandpass_filter.get("lp_sigma"),
                    bandpass_filter.get("hp_sigma"),
                )

                strings = []
                if lp_sigma is not None:
                    strings.append(f"a low-pass filter width of {lp_sigma} seconds")
                if hp_sigma is not None:
                    strings.append(f"a high-pass filter width of {hp_sigma} seconds")

                if len(strings) > 0:
                    self.choice = "No"
                    self._append_view(TextView(f"with {p.join(strings)}"))
                self._append_view(SpacerView(1))

            elif type == "frequency_based":
                self.yes_step_type = FrequencyBasedBandpassSettingStep

                message = "Temporal filtering will be applied using a frequency-based filter"
                self._append_view(TextView(message))

                low, high = bandpass_filter.get("low"), bandpass_filter.get("high")

                strings = []
                if low is not None:
                    strings.append(f"a low cutoff of {low} Hz")
                if low is not None:
                    strings.append(f"a high cutoff of {high} Hz")

                if len(strings) > 0:
                    self.choice = "No"
                    self._append_view(TextView(f"with {p.join(strings)}"))
                self._append_view(SpacerView(1))

            return False

    class GrandMeanScalingSettingStep(Step):
        noun = "grand mean"

        def setup(self, ctx):
            self._append_view(TextView(f"Specify {self.noun}"))

            suggestion = 10000.0

            featuresettings = set(
                feature.setting for feature in ctx.spec.features if hasattr(feature, "setting")
            )

            self.means = list()
            for setting in ctx.spec.settings:
                if not setting.get("output_image", False) and setting["name"] not in featuresettings:
                    continue

                grand_mean_scaling = setting.get("grand_mean_scaling")
                if grand_mean_scaling is not None:
                    mean = grand_mean_scaling.get("mean")
                    if mean is not None:
                        self.means.append(mean)

            self.means = list(unique_everseen(self.means))

            if len(self.means) > 0:
                suggestion = float(self.means[-1])

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

            ctx.spec.settings[-1]["grand_mean_scaling"] = GrandMeanScalingSettingSchema().load(
                {"mean": self._value}
            )

            this_next_step_type = DoBandpassFilterStep

            if len(self.means) == 1 and self._value not in self.means:
                return ConfirmInconsistentStep(self.app, f"{self.noun} values", this_next_step_type)(ctx)

            return this_next_step_type(self.app)(ctx)

    class DoGrandMeanScalingStep(YesNoStep):
        header_str = "Do grand mean scaling?"
        yes_step_type = GrandMeanScalingSettingStep
        no_step_type = DoBandpassFilterStep

        def _should_run(self, ctx):
            if "grand_mean_scaling" not in ctx.spec.settings[-1]:
                return True

            self.choice = "Yes"

            grand_mean_scaling = ctx.spec.settings[-1]["grand_mean_scaling"]

            if grand_mean_scaling is None:
                self.choice = "No"

                message = "No grand mean scaling will be done"
                self._append_view(TextView(message))
                self._append_view(SpacerView(1))

            else:
                mean = grand_mean_scaling.get("mean")

                message = "Grand mean scaling will be applied"

                if mean is not None:
                    self.choice = "No"

                    assert isinstance(mean, float)
                    message = f"{message} with a mean of {mean:f}"

                self._append_view(TextView(message))
                self._append_view(SpacerView(1))

            return False

    class SmoothingSettingStep(Step):
        noun = "smoothing FWHM"

        def setup(self, ctx):
            self._append_view(TextView(f"Specify {self.noun} in mm"))

            suggestion = 6.0

            featuresettings = set(
                feature.setting for feature in ctx.spec.features if hasattr(feature, "setting")
            )

            self.fwhms = list()
            for setting in ctx.spec.settings:
                if not setting.get("output_image", False) and setting["name"] not in featuresettings:
                    continue

                smoothing = setting.get("smoothing")
                if smoothing is not None:
                    fwhm = smoothing["fwhm"]
                    self.fwhms.append(fwhm)

            self.fwhms = list(unique_everseen(self.fwhms))

            if len(self.fwhms) > 0:
                suggestion = float(self.fwhms[-1])

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

            ctx.spec.settings[-1]["smoothing"] = SmoothingSettingSchema().load(
                {"fwhm": self._value}
            )

            this_next_step_type = DoGrandMeanScalingStep

            if len(self.fwhms) == 1 and self._value not in self.fwhms:
                return ConfirmInconsistentStep(self.app, f"{self.noun} values", this_next_step_type)(ctx)

            return this_next_step_type(self.app)(ctx)

    class DoSmoothingStep(YesNoStep):
        header_str = "Apply smoothing?"
        yes_step_type = SmoothingSettingStep
        no_step_type = DoGrandMeanScalingStep

        def _should_run(self, ctx):
            if "smoothing" not in ctx.spec.settings[-1]:
                return True

            self.choice = "Yes"

            smoothing = ctx.spec.settings[-1]["smoothing"]

            if smoothing is None:
                self.choice = "No"

                message = "No smoothing will be applied"
                self._append_view(TextView(message))
                self._append_view(SpacerView(1))

            else:
                fwhm = smoothing.get("fwhm")

                message = "Smoothing will be applied"

                if fwhm is not None:
                    self.choice = "No"

                    message = f"{message} with an FWHM of {fwhm} mm"

                self._append_view(TextView(message))
                self._append_view(SpacerView(1))

            return False

        def setup(self, ctx):
            if vals_header_str is not None:
                self._append_view(TextView(vals_header_str))
                self._append_view(SpacerView(1))

            super(DoSmoothingStep, self).setup(ctx)

        def next(self, ctx):
            if "smoothing" in ctx.spec.settings[-1]:
                smoothing = ctx.spec.settings[-1]["smoothing"]
                if self.choice == "No" and smoothing is None:
                    del ctx.spec.settings[-1]["smoothing"]  # remove empty
            return super(DoSmoothingStep, self).next(ctx)

    return DoSmoothingStep
