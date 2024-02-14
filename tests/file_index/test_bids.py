# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from halfpipe.file_index.bids import parse


def test_parse():
    path = Path("qtab/reports/sub-0003/figures/sub-0003_task-emotionalconflict_epi_norm_rpt.svg")
    tags = parse(path)

    assert isinstance(tags, dict)
    assert len(tags) == 4

    assert tags["sub"] == "0003"
    assert tags["task"] == "emotionalconflict"
    assert tags["suffix"] == "epi_norm_rpt"
    assert tags["extension"] == ".svg"

    path = Path("qtab/derivatives/halfpipe/sub-0003/func")
    tags = parse(path)

    assert isinstance(tags, dict)
    assert len(tags) == 1

    assert tags["suffix"] == "func"

    path = Path("qtab/derivatives/fmriprep/sub-0194/anat/sub-0194_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5")
    tags = parse(path)

    assert isinstance(tags, dict)
    assert len(tags) == 7

    assert tags["sub"] == "0194"
    assert tags["from"] == "T1w"
    assert tags["to"] == "MNI152NLin2009cAsym"
    assert tags["mode"] == "image"
    assert tags["suffix"] == "xfm"
    assert tags["datatype"] == "anat"
    assert tags["extension"] == ".h5"
