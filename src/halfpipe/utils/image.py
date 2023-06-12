# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def nifti_dim(obj, dimension_index: int) -> int:
    if isinstance(obj, str):
        import nibabel as nib

        obj = nib.load(obj)

    if len(obj.shape) > dimension_index:
        return obj.shape[dimension_index]

    return 1


def nvol(obj) -> int:
    from halfpipe.utils.image import nifti_dim

    return nifti_dim(obj, 3)
