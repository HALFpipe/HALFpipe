# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from ...model import RefFileSchema
from ...utils.copy import deepcopy
from ...utils.format import format_like_bids
from ..components import (
    CombinedMultipleAndSingleChoiceInputView,
    NumberInputView,
    SpacerView,
    TextView,
)
from ..metadata import CheckMetadataStep
from ..pattern import FilePatternStep
from ..setting import get_setting_init_steps, get_setting_vals_steps
from ..step import Step
from .loop import AddAnotherFeatureStep, SettingValsStep

next_step_type = SettingValsStep


def get_ref_steps(suffix, featurefield, dsp_str, ref_next_step_type):
    class CheckSpaceStep(CheckMetadataStep):
        schema = RefFileSchema
        key = "space"

    class AddStep(FilePatternStep):
        filetype_str = f"{dsp_str} image"
        filedict = {"datatype": "ref", "suffix": suffix}
        entity_display_aliases = {"desc": suffix}

        schema = RefFileSchema

        ask_if_missing_entities = ["desc"]
        required_in_path_entities = []

        next_step_type = CheckSpaceStep

    class SelectStep(Step):
        entity = "desc"

        filters = {"datatype": "ref", "suffix": suffix}

        header_str = f"Specify {dsp_str} file(s)"
        filetype_str = f"{dsp_str} image"

        def setup(self, ctx):
            self.choice = None
            self.is_first_run = True

            if self.header_str is not None:
                self._append_view(TextView(self.header_str))

            filepaths = ctx.database.get(**self.filters)
            tagvals = ctx.database.tagvalset(self.entity, filepaths=filepaths)

            self.is_missing = True

            self.choice = None
            if tagvals is not None and len(tagvals) > 0:
                self.is_missing = False

                self.add_file_str = f"Add {self.filetype_str} file"

                dsp_values = [f'"{value}"' for value in tagvals]

                self.tagval_by_str = dict(zip(dsp_values, tagvals))

                self.input_view = CombinedMultipleAndSingleChoiceInputView(
                    dsp_values, [self.add_file_str], checked=dsp_values, isVertical=True
                )

                self._append_view(self.input_view)
                self._append_view(SpacerView(1))

        def run(self, _):
            if self.is_missing:
                return self.is_first_run
            else:
                self.choice = self.input_view()
                if self.choice is None:
                    return False
                return True

        def next(self, ctx):
            if self.choice is not None and isinstance(self.choice, dict):
                tagvals = [
                    self.tagval_by_str[dsp_str]
                    for dsp_str, is_selected in self.choice.items()
                    if is_selected
                ]
                setattr(ctx.spec.features[-1], featurefield, tagvals)

            if (self.is_first_run and self.is_missing) or (
                not self.is_missing and self.choice == self.add_file_str
            ):
                self.is_first_run = False
                return AddStep(self.app)(ctx)

            elif self.is_first_run or not self.is_missing:
                self.is_first_run = False
                return ref_next_step_type(self.app)(ctx)

    CheckSpaceStep.next_step_type = SelectStep

    return SelectStep


class MinSeedCoverageStep(Step):
    noun = "minimum seed coverage"
    suggestion = 0.8

    def setup(self, ctx):
        self.result = None

        self._append_view(TextView(f"Specify {self.noun} by individual brain mask"))
        self._append_view(
            TextView(
                "Functional images that do not meet the requirement will be skipped"
            )
        )

        self.valset = set()

        for feature in ctx.spec.features[:-1]:
            if feature.type == "seed_based_connectivity":
                min_seed_coverage = getattr(feature, "min_seed_coverage", None)
                if min_seed_coverage is not None:
                    self.valset.add(min_seed_coverage)

        suggestion = self.suggestion
        if len(self.valset) > 0:
            suggestion = next(iter(self.valset))

        self.input_view = NumberInputView(number=suggestion, min=0, max=1.0)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        if self.result is not None and isinstance(self.result, float):
            ctx.spec.features[-1].min_seed_coverage = self.result

        this_next_step_type = next_step_type

        return this_next_step_type(self.app)(ctx)


SeedBasedConnectivityRefStep = get_ref_steps(
    "seed", "seeds", "binary seed mask", MinSeedCoverageStep
)
DualRegressionRefStep = get_ref_steps("map", "maps", "spatial map", next_step_type)


class AtlasBasedMinRegionCoverageStep(Step):
    noun = "minimum atlas region coverage"
    suggestion = 0.8

    def setup(self, ctx):
        self.result = None

        self._append_view(TextView(f"Specify {self.noun} by individual brain mask"))
        self._append_view(
            TextView(
                "Atlas region signals that do not reach the requirement are set to n/a"
            )
        )

        self.valset = set()

        for feature in ctx.spec.features[:-1]:
            if feature.type == "atlas_based_connectivity":
                min_region_coverage = getattr(feature, "min_region_coverage", None)
                if min_region_coverage is not None:
                    self.valset.add(min_region_coverage)

        suggestion = self.suggestion
        if len(self.valset) > 0:
            suggestion = next(iter(self.valset))

        self.input_view = NumberInputView(number=suggestion, min=0, max=1.0)

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, _):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        if self.result is not None and isinstance(self.result, float):
            ctx.spec.features[-1].min_region_coverage = self.result

        this_next_step_type = next_step_type

        return this_next_step_type(self.app)(ctx)


AtlasBasedConnectivityRefStep = get_ref_steps(
    "atlas", "atlases", "atlas", AtlasBasedMinRegionCoverageStep
)


SeedBasedConnectivitySettingInitStep = get_setting_init_steps(
    SeedBasedConnectivityRefStep,
    settingdict={"grand_mean_scaling": {"mean": 10000.0}},
)
DualRegressionSettingInitStep = get_setting_init_steps(
    DualRegressionRefStep,
    settingdict={
        "bandpass_filter": {"type": "gaussian"},
        "grand_mean_scaling": {"mean": 10000.0},
    },
)
AtlasBasedConnectivitySettingInitStep = get_setting_init_steps(
    AtlasBasedConnectivityRefStep,
    settingdict={"smoothing": None, "grand_mean_scaling": {"mean": 10000.0}},
)

settingdict = {
    "bandpass_filter": {"type": "frequency_based", "low": 0.01, "high": 0.1},
    "grand_mean_scaling": {"mean": 10000.0},
}


def move_setting_smoothing_to_feature(ctx):
    if ctx.spec.settings[-1].get("smoothing") is not None:
        smoothing = ctx.spec.settings[-1]["smoothing"]
        del ctx.spec.settings[-1]["smoothing"]
        ctx.spec.features[-1].smoothing = smoothing


def on_falff_setting(ctx):
    move_setting_smoothing_to_feature(ctx)

    name = format_like_bids(f"{ctx.spec.features[-1].name} unfiltered setting")

    unfiltered_setting = deepcopy(ctx.spec.settings[-1])
    unfiltered_setting["name"] = name
    del unfiltered_setting[
        "bandpass_filter"
    ]  # remove bandpass filter, keep everything else
    ctx.spec.settings.append(unfiltered_setting)

    ctx.spec.features[-1].unfiltered_setting = name


ReHoSettingValsStep = get_setting_vals_steps(
    AddAnotherFeatureStep, oncompletefn=move_setting_smoothing_to_feature
)
ReHoSettingInitStep = get_setting_init_steps(
    ReHoSettingValsStep, settingdict=settingdict
)

FALFFSettingValsStep = get_setting_vals_steps(
    AddAnotherFeatureStep, oncompletefn=on_falff_setting
)
FALFFSettingInitStep = get_setting_init_steps(
    FALFFSettingValsStep, settingdict=settingdict
)

SeedBasedConnectivityStep = SeedBasedConnectivitySettingInitStep
DualRegressionStep = DualRegressionSettingInitStep
AtlasBasedConnectivityStep = AtlasBasedConnectivitySettingInitStep
ReHoStep = ReHoSettingInitStep
FALFFStep = FALFFSettingInitStep
