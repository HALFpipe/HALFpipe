# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from typing import Any, Literal
from unittest import mock

import pytest

from halfpipe.ui.components import (
    MultiCombinedNumberAndSingleChoiceInputView,
    MultipleChoiceInputView,
)
from halfpipe.ui.components.input.choice import SingleChoiceInputView
from halfpipe.ui.setting.vals import get_setting_vals_steps
from halfpipe.ui.step import Context, Step

from ..mock import MockApp


@pytest.mark.parametrize(
    "bandpass_filter",
    [
        (
            "frequency_based",
            {
                "Low cutoff": 0.1,
                "High cutoff": "Skip",
            },
            {"low": 0.1, "high": None},
        ),
        (
            "frequency_based",
            {
                "Low cutoff": 0.1,
                "High cutoff": 0.2,
            },
            {"low": 0.1, "high": 0.2},
        ),
        (
            "gaussian",
            {
                "Low-pass width": 128.0,
                "High-pass width": "Skip",
            },
            {"lp_width": 128.0, "hp_width": None},
        ),
    ],
)
@pytest.mark.parametrize(
    "space", [("Standard space (MNI ICBM 2009c Nonlinear Asymmetric)", "standard"), ("Native space", "native")]
)
def test_setting_vals(
    bandpass_filter: tuple[str, dict[str, float | Literal["Skip"]], dict[str, float | None]], space: tuple[str, str]
) -> None:
    type, bandpass_filter_ui_return_value, bandpass_filter_expected = bandpass_filter
    space_ui_return_value, space_expected = space

    app = MockApp()

    def mock_next_step_type(_):
        def mock_next_step(ctx):
            return ctx

        return mock_next_step

    step = get_setting_vals_steps(mock_next_step_type)
    assert issubclass(step, Step)

    ctx = Context()
    spec = ctx.spec

    spec.settings.append(
        dict(
            name="a",
            smoothing=None,
            grand_mean_scaling=None,
            bandpass_filter=dict(type=type),
        )
    )

    with (
        mock.patch.object(MultiCombinedNumberAndSingleChoiceInputView, "__call__") as mcnsc,
        mock.patch.object(MultipleChoiceInputView, "__call__") as mc,
        mock.patch.object(SingleChoiceInputView, "__call__") as sc,
    ):
        instance: Any = step(app)

        mcnsc.return_value = bandpass_filter_ui_return_value

        sc.return_value = space_ui_return_value

        confounds_valuedict = defaultdict(lambda: False)
        confounds_valuedict["ICA-AROMA"] = True
        mc.return_value = confounds_valuedict
        new_ctx = instance(ctx)

    for key, value in bandpass_filter_expected.items():
        assert new_ctx.spec.settings[-1]["bandpass_filter"][key] == value

    assert new_ctx.spec.settings[-1]["space"] == space_expected

    assert new_ctx.spec.settings[-1]["ica_aroma"] is True
    assert "confounds_removal" not in new_ctx.spec.settings[-1]
