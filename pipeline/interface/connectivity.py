# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Nipype interfaces to calculate connectivity measures using nilearn.
Adapted from https://github.com/Neurita/pypes
"""
from os import path as op

import numpy as np
import nibabel as nib
import pandas as pd

from scipy.ndimage.measurements import mean
from nilearn.connectome.connectivity_matrices import prec_to_partial

from nipype.interfaces.base import (
    BaseInterface,
    TraitedSpec,
    BaseInterfaceInputSpec,
    traits,
)

from ..utils import nvol


def _img_to_signals(in_file, mask_file, atlas_file, background_label=0, min_n_voxels=50):
    in_img = nib.load(in_file)

    atlas_img = nib.load(atlas_file)
    assert nvol(atlas_img) == 1
    assert atlas_img.shape[:3] == in_img.shape[:3]
    assert np.allclose(atlas_img.affine, in_img.affine)

    mask_img = nib.load(mask_file)
    assert nvol(mask_img) == 1
    assert mask_img.shape[:3] == in_img.shape[:3]
    assert np.allclose(mask_img.affine, in_img.affine)

    labels = np.asanyarray(atlas_img.dataobj).astype(np.int32)
    nlabel = labels.max()
    mask_data = np.asanyarray(mask_img.dataobj).astype(np.bool)

    labels[np.logical_not(mask_data)] = background_label
    assert np.all(labels >= 0)

    indices, counts = np.unique(labels, return_counts=True)
    indices = indices[counts >= min_n_voxels]
    indices = np.setdiff1d(indices, [background_label])

    in_data = in_img.get_fdata()
    if in_data.ndim == 3:
        in_data = in_data[:, :, :, np.newaxis]
    assert in_data.ndim == 4

    result = np.full((in_data.shape[3], nlabel), np.nan)
    for i, img in enumerate(np.moveaxis(in_data, 3, 0)):
        result[i, indices - 1] = mean(img, labels=labels, index=indices)

    return result


class ConnectivityMeasureInputSpec(BaseInterfaceInputSpec):
    in_file = traits.File(
        desc="Image file(s) from where to extract the data", exists=True, mandatory=True
    )
    mask_file = traits.File(desc="Mask file", exists=True, mandatory=True)
    atlas_file = traits.File(
        desc="Atlas image file defining the connectivity ROIs", exists=True, mandatory=True,
    )

    background_label = traits.Int(desc="", default=0,)
    min_n_voxels = traits.Int(desc="", default=50,)


class ConnectivityMeasureOutputSpec(TraitedSpec):
    time_series = traits.File(desc="Numpy text file with the timeseries matrix")
    covariance = traits.File(desc="Numpy text file with the connectivity matrix")
    correlation = traits.File(desc="Numpy text file with the connectivity matrix")
    partial_correlation = traits.File(desc="Numpy text file with the connectivity matrix")


class ConnectivityMeasure(BaseInterface):
    input_spec = ConnectivityMeasureInputSpec
    output_spec = ConnectivityMeasureOutputSpec

    def _run_interface(self, runtime):
        self._time_series = _img_to_signals(
            self.inputs.in_file,
            self.inputs.mask_file,
            self.inputs.atlas_file,
            background_label=self.inputs.background_label,
            min_n_voxels=self.inputs.min_n_voxels,
        )

        df = pd.DataFrame(self._time_series)

        self._cov_mat = np.asarray(df.cov())
        self._corr_mat = np.asarray(df.corr())
        self._pcorr_mat = prec_to_partial(np.linalg.inv(self._cov_mat))

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()

        time_series_file = op.abspath("timeseries.txt")
        np.savetxt(time_series_file, self._time_series, fmt="%.10f")

        covariance_file = op.abspath("timeseries.txt")
        np.savetxt(covariance_file, self._cov_mat, fmt="%.10f")

        correlation_file = op.abspath("timeseries.txt")
        np.savetxt(correlation_file, self._corr_mat, fmt="%.10f")

        partial_correlation_file = op.abspath("partial_correlation.txt")
        np.savetxt(partial_correlation_file, self._pcorr_mat, fmt="%.10f")

        outputs["time_series"] = time_series_file
        outputs["covariance"] = covariance_file
        outputs["correlation"] = correlation_file
        outputs["partial_correlation"] = partial_correlation_file
        return outputs
