# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Nipype interfaces to calculate connectivity measures using nilearn.
Adapted from https://github.com/Neurita/pypes
"""
from os import path as op

import numpy as np
import pandas as pd

from nilearn.connectome.connectivity_matrices import prec_to_partial

from nipype.interfaces.base import (
    BaseInterface,
    TraitedSpec,
    BaseInterfaceInputSpec,
    traits,
)

from ..io import img_to_signals


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
        self._time_series = img_to_signals(
            self.inputs.in_file,
            self.inputs.atlas_file,
            mask_file=self.inputs.mask_file,
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
