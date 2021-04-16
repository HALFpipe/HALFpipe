# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def niftidim(input, idim: int) -> int:
    if isinstance(input, str):
        import nibabel as nib

        input = nib.load(input)
    if len(input.shape) > idim:
        return input.shape[idim]
    else:
        return 1


def nvol(input) -> int:
    from halfpipe.utils import niftidim

    return niftidim(input, 3)
