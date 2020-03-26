# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Nipype interfaces to calculate connectivity measures using nilearn.
Adapted from https://github.com/Neurita/pypes
"""
from os import path as op

import nilearn.connectome
import numpy as np
from nilearn.input_data import NiftiMapsMasker, NiftiLabelsMasker
from nipype.interfaces.base import (
    BaseInterface,
    TraitedSpec,
    BaseInterfaceInputSpec,
    traits,
)


class ConnectivityMeasureInputSpec(BaseInterfaceInputSpec):
    in_file = traits.File(
        desc="Image file(s) from where to extract the data", exists=True, mandatory=True
    )
    mask_file = traits.File(desc="Mask file", exists=True, mandatory=True)
    atlas_file = traits.File(
        desc="Atlas image file defining the connectivity ROIs",
        exists=True,
        mandatory=True,
    )
    atlas_type = traits.Enum(
        "probabilistic", "labels", desc="The type of atlas", default="labels"
    )

    standardize = traits.Either(
        False,
        traits.Enum("zscore", "psc"),
        desc="Strategy to standardize the signal",
        default=False,
    )
    resampling_target = traits.Either(
        None,
        traits.Enum("data", "labels"),
        desc="Gives which image gives the final shape/size",
        default=None,
    )

    kind = traits.Enum(
        "correlation",
        "partial correlation",
        "tangent",
        "covariance",
        "precision",
        desc="The connectivity matrix kind",
        default="covariance",
    )


class ConnectivityMeasureOutputSpec(TraitedSpec):
    connectivity = traits.File(desc="Numpy text file with the connectivity matrix")
    timeseries = traits.File(desc="Numpy text file with the timeseries matrix")


class ConnectivityMeasure(BaseInterface):
    """
    For more information look at: nilearn.connectome.ConnectivityMeasure
    """

    input_spec = ConnectivityMeasureInputSpec
    output_spec = ConnectivityMeasureOutputSpec

    def _run_interface(self, runtime):
        self._time_series_file = op.abspath("conn_timeseries.txt")
        self._conn_mat_file = op.abspath("connectivity.txt")

        niftiMasker = NiftiLabelsMasker
        if self.inputs.atlas_type == "probabilistic":
            niftiMasker = NiftiMapsMasker

        masker = niftiMasker(
            labels_img=self.inputs.atlas_file,
            background_label=0,
            mask_img=self.inputs.mask_file,
            smoothing_fwhm=None,
            standardize=self.inputs.standardize,
            resampling_target=self.inputs.resampling_target,
            memory="nilearn_cache",
            verbose=5,
        )

        self._time_series = masker.fit_transform(self.inputs.in_file)

        conn_measure = nilearn.connectome.ConnectivityMeasure(kind=self.inputs.kind)
        self._conn_mat = conn_measure.fit_transform([self._time_series])

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()

        np.savetxt(self._time_series_file, self._time_series, fmt="%.10f")
        np.savetxt(self._conn_mat_file, self._conn_mat.squeeze(), fmt="%.10f")

        outputs["timeseries"] = self._time_series_file
        outputs["connectivity"] = self._conn_mat_file
        return outputs
