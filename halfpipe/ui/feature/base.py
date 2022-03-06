# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ...model import Feature
from ..components import SingleChoiceInputView, SpacerView, TextInputView, TextView
from ..step import Step, YesNoStep
from ..utils import forbidden_chars
from .imageoutput import ImageOutputStep
from .loop import AddAnotherFeatureStep
from .rest import (
    AtlasBasedConnectivityStep,
    DualRegressionStep,
    FALFFStep,
    ReHoStep,
    SeedBasedConnectivityStep,
)
from .task import TaskBasedStep


class FeatureNameStep(Step):
    suggestions_by_type = {
        "task_based": "taskBased",
        "seed_based_connectivity": "seedCorr",
        "dual_regression": "dualReg",
        "atlas_based_connectivity": "corrMatrix",
        "reho": "reHo",
        "falff": "fALFF",
    }

    def setup(self, ctx):
        self._append_view(TextView("Specify feature name"))

        assert ctx.spec.features is not None and len(ctx.spec.features) > 0

        self.names = set(feature.name for feature in ctx.spec.features)

        base = self.suggestions_by_type[ctx.spec.features[-1].type]
        suggestion = base
        index = 1
        while suggestion in self.names:
            suggestion = f"{base}{index}"
            index += 1

        self.input_view = TextInputView(
            text=suggestion, isokfun=lambda text: forbidden_chars.search(text) is None
        )

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.result = self.input_view()
        if self.result is None:  # was cancelled
            return False
        return True

    def next(self, ctx):
        assert self.result not in self.names, "Duplicate feature name"

        ctx.spec.features[-1].name = self.result

        next_step_type = {
            "task_based": TaskBasedStep,
            "seed_based_connectivity": SeedBasedConnectivityStep,
            "dual_regression": DualRegressionStep,
            "atlas_based_connectivity": AtlasBasedConnectivityStep,
            "reho": ReHoStep,
            "falff": FALFFStep,
        }[ctx.spec.features[-1].type]

        return next_step_type(self.app)(ctx)


class FeatureTypeStep(Step):
    options = {
        "Task-based": "task_based",
        "Seed-based connectivity": "seed_based_connectivity",
        "Dual regression": "dual_regression",
        "Atlas-based connectivity matrix": "atlas_based_connectivity",
        "ReHo": "reho",
        "fALFF": "falff",
    }

    def setup(self, ctx):
        self._append_view(TextView("Specify the feature type"))

        self.input_view = SingleChoiceInputView(
            list(self.options.keys()), isVertical=True
        )

        self._append_view(self.input_view)
        self._append_view(SpacerView(1))

    def run(self, ctx):
        self.choice = self.input_view()
        if self.choice is None:
            return False
        return True

    def next(self, ctx):
        if self.choice is None:
            return

        featureobj = Feature(name=None, type=self.options[self.choice])
        ctx.spec.features.append(featureobj)

        return FeatureNameStep(self.app)(ctx)


class SpecifyFeaturesStep(YesNoStep):
    header_str = "Specify first-level features?"
    yes_step_type = FeatureTypeStep
    no_step_type = ImageOutputStep


AddAnotherFeatureStep.yes_step_type = FeatureTypeStep
FeaturesStep = SpecifyFeaturesStep
