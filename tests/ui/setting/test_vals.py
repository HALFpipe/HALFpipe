# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from typing import Any
from unittest import mock

import pytest

from halfpipe.ui.components import (
    MultiCombinedNumberAndSingleChoiceInputView,
    MultipleChoiceInputView,
)
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
def test_setting_vals(bandpass_filter) -> None:
    type, ui_return_value, expected = bandpass_filter

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
    ):
        instance: Any = step(app)

        mcnsc.return_value = ui_return_value

        confounds_valuedict = defaultdict(lambda: False)
        confounds_valuedict["ICA-AROMA"] = True
        mc.return_value = confounds_valuedict
        new_ctx = instance(ctx)

    for key, value in expected.items():
        assert new_ctx.spec.settings[-1]["bandpass_filter"][key] == value

    assert new_ctx.spec.settings[-1]["ica_aroma"] is True
    assert "confounds_removal" not in new_ctx.spec.settings[-1]
