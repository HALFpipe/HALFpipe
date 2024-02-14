# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from unittest import mock

import pytest
from halfpipe.ui.components import MultiCombinedNumberAndSingleChoiceInputView
from halfpipe.ui.file.func import get_post_func_steps
from halfpipe.ui.step import Context, Step, YesNoStep

from ..mock import MockApp


@pytest.mark.parametrize("value", ["detect_str", 0, 5])
def test_dummy_scans_step(value: str | int | None) -> None:
    app = MockApp()

    do_slice_timing_step = get_post_func_steps(None)
    assert issubclass(do_slice_timing_step, YesNoStep)
    dummy_scans_step_type: type[Step] | None = do_slice_timing_step.no_step_type
    assert dummy_scans_step_type is not None
    assert issubclass(dummy_scans_step_type, Step)

    ctx = Context()
    spec = ctx.spec

    with mock.patch.object(MultiCombinedNumberAndSingleChoiceInputView, "__call__") as call:
        dummy_scans_step = dummy_scans_step_type(app)
        assert hasattr(dummy_scans_step, "next_step_type")
        dummy_scans_step.next_step_type = None

        if value == "detect_str":
            assert hasattr(dummy_scans_step, "detect_str")
            call.return_value = {"": dummy_scans_step.detect_str}
            value = None
        else:
            call.return_value = {"": value}

        spec.global_settings["dummy_scans"] = 42

        new_ctx = dummy_scans_step(ctx)
        assert new_ctx is not None

        assert new_ctx.spec.global_settings["dummy_scans"] is value
