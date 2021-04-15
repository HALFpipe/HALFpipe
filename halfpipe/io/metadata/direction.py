# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import nibabel as nib
import re

from calamities.pattern import tag_glob

from ...model.metadata import direction_codes, axis_codes, space_codes
from .niftiheader import NiftiheaderLoader


def get_axcodes_set(pat):
    tagglobres = tag_glob(pat)
    filepaths, _ = zip(*tagglobres)

    axcodes_set = set()

    for filepath in filepaths:
        header, _ = NiftiheaderLoader.load(filepath)
        axcodes_set.add(nib.aff2axcodes(header.get_qform()))

    return axcodes_set


def parse_direction_str(s):
    if s in direction_codes:
        return s
    else:
        s = s.lower()
        s = re.sub(r"[^a-z]", "", s)  # keep only letters
        if s in direction_codes:
            return s
        elif s == "righttoleft":
            return "rl"
        elif s == "lefttoright":
            return "lr"
        elif s == "posteriortoanterior":
            return "pa"
        elif s == "anteriortoposterior":
            return "ap"
        elif s == "superiortoinferior":
            return "si"
        elif s == "inferiortosuperior":
            return "is"
    raise ValueError(f'Unknown phase encoding direction string "{s}"')


def invert_location(d):
    return {"r": "l", "l": "r", "p": "a", "a": "p", "s": "i", "i": "s"}[d]


def canonicalize_direction_code(pedir_code, pat):
    canonical_pedir_code = pedir_code
    if pedir_code not in axis_codes:
        assert pedir_code in space_codes, "Unknown phase encoding direction code"
        axcodes_set = get_axcodes_set(pat)
        assert len(axcodes_set) == 1, "Inconsistent axis orientations"
        axcodes = axcodes_set.pop()
        for i, axcode in enumerate(axcodes):
            axcode = axcode.lower()
            if axcode in pedir_code:
                canonical_pedir_code = ["i", "j", "k"][i]
                if pedir_code[0] == axcode:
                    canonical_pedir_code += "-"
                break
    assert canonical_pedir_code in axis_codes, "Unknown phase encoding direction code"
    return canonical_pedir_code


def direction_code_str(pedir_code, pat):
    if pedir_code not in space_codes:
        assert pedir_code in axis_codes, "Unknown phase encoding direction code"

        axcodes_set = get_axcodes_set(pat)
        assert len(axcodes_set) == 1, "Inconsistent axis orientations"
        (axcodes,) = axcodes_set

        location_to = axcodes[["i", "j", "k"].index(pedir_code[0])].lower()
        if pedir_code.endswith("-"):
            location_to = invert_location(location_to)
        location_from = invert_location(location_to)

        pedir_code = f"{location_from}{location_to}"

    assert pedir_code in space_codes, "Unknown phase encoding direction code"

    return {
        "rl": "right to left",
        "lr": "left to right",
        "pa": "posterior to anterior",
        "ap": "anterior to posterior",
        "si": "superior to inferior",
        "is": "inferior to superior",
    }[pedir_code]
