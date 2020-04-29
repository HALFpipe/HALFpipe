# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import nibabel as nib

from calamities import tag_glob


def get_axcodes_set(pat):
    tagglobres = tag_glob(pat)
    filepaths, _ = zip(*tagglobres)
    return set(
        nib.aff2axcodes(nib.load(filepath, mmap=False, keep_file_open=False).affine)
        for filepath in filepaths
    )


def canonicalize_pedir_str(pedir_str, pat):
    canonical_pedir_strs = {"i-", "i", "j-", "j", "k-", "k"}
    if pedir_str not in canonical_pedir_strs:
        assert pedir_str in {
            "rl",
            "lr",
            "pa",
            "ap",
            "si",
            "is",
        }, "Unknown phase encoding direction code"
        axcodes_set = get_axcodes_set(pat)
        assert len(axcodes_set) == 1, "Inconsistent axis orientations"
        axcodes = axcodes_set.pop()
        for i, axcode in enumerate(axcodes):
            axcode = axcode.lower()
            if axcode in pedir_str:
                canonical_pedir_str = ["i", "j", "k"][i]
                if pedir_str[0] == axcode:
                    canonical_pedir_str += "-"
                break
    assert canonical_pedir_str in canonical_pedir_strs, "Unknown phase encoding direction code"
    return canonical_pedir_str
