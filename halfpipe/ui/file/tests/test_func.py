# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Any
from unittest import mock

import pytest

from ...base import Context
from ...components import MultiCombinedNumberAndSingleChoiceInputView
from ...step import Step, YesNoStep
from ...tests.mock import MockApp
from ..func import get_post_func_steps


@pytest.mark.parametrize("value", ["detect_str", 0, 5])
def test_dummy_scans_step(value):
    app = MockApp()

    DoSliceTimingStep = get_post_func_steps(None)
    assert issubclass(DoSliceTimingStep, YesNoStep)
    DummyScansStep = DoSliceTimingStep.no_step_type
    assert DummyScansStep is not None
    assert issubclass(DummyScansStep, Step)

    ctx = Context()
    spec = ctx.spec

    with mock.patch.object(
        MultiCombinedNumberAndSingleChoiceInputView, "__call__"
    ) as call:
        dummy_scans_step: Any = DummyScansStep(app)
        dummy_scans_step.next_step_type = None

        if value == "detect_str":
            call.return_value = {"": dummy_scans_step.detect_str}
            value = None
        else:
            call.return_value = {"": value}

        spec.global_settings["dummy_scans"] = 42

        new_ctx = dummy_scans_step(ctx)

        assert new_ctx.spec.global_settings["dummy_scans"] is value
