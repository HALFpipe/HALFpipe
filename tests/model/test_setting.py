# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from halfpipe.model.setting import BandpassFilterSettingSchema


def test_null_bandpass_filter():
    schema = BandpassFilterSettingSchema()

    b = schema.load(
        dict(
            type="frequency_based",
            low=0.1,
            high=None,
        )
    )
    assert isinstance(b, dict)

    b = schema.load(
        dict(
            type="frequency_based",
            low=0.1,
        )
    )
    assert isinstance(b, dict)
