# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op
from pathlib import Path
from typing import Literal, overload

import nibabel as nib
import numpy as np
import pandas as pd
from nipype.interfaces.base import (
    BaseInterface,
    BaseInterfaceInputSpec,
    File,
    TraitedSpec,
    traits,
)
from scipy.ndimage import mean

from ..utils.image import nvol
from ..utils.matrix import atleast_4d


@overload
def mean_signals(
    in_file: str | Path,
    atlas_file: str | Path,
    output_coverage: Literal[False] = False,
    mask_file: str | Path | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
) -> np.ndarray:
    ...


@overload
def mean_signals(
    in_file: str | Path,
    atlas_file: str | Path,
    output_coverage: Literal[True],
    mask_file: str | Path | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
) -> tuple[np.ndarray, list[float]]:
    ...


def mean_signals(
    in_file: str | Path,
    atlas_file: str | Path,
    output_coverage: bool = False,
    mask_file: str | Path | None = None,
    background_label: int = 0,
    min_region_coverage: float = 0,
):
    in_img = nib.load(in_file)
    atlas_img = nib.load(atlas_file)

    assert nvol(atlas_img) == 1
    assert atlas_img.shape[:3] == in_img.shape[:3]
    assert np.allclose(atlas_img.affine, in_img.affine)

    labels = np.asanyarray(atlas_img.dataobj).astype(int)

    nlabel: int = labels.max()

    assert background_label <= nlabel

    indices = np.arange(0, nlabel + 1, dtype=int)

    out_region_coverage = None

    if mask_file is not None:
        mask_img = nib.load(mask_file)

        assert nvol(mask_img) == 1
        assert mask_img.shape[:3] == in_img.shape[:3]
        assert np.allclose(mask_img.affine, in_img.affine)

        mask_data = np.asanyarray(mask_img.dataobj).astype(bool)

        unmasked_counts = np.bincount(np.ravel(labels), minlength=nlabel + 1)[
            : nlabel + 1
        ]

        labels[np.logical_not(mask_data)] = background_label

        masked_counts = np.bincount(np.ravel(labels), minlength=nlabel + 1)[
            : nlabel + 1
        ]

        region_coverage = masked_counts.astype(float) / unmasked_counts.astype(float)
        region_coverage[unmasked_counts == 0] = 0

        out_region_coverage = list(region_coverage[indices != background_label])
        assert len(out_region_coverage) == nlabel

        indices = indices[region_coverage >= min_region_coverage]

    indices = indices[indices != background_label]

    assert np.all(labels >= 0)

    in_data = atleast_4d(in_img.get_fdata())

    result = np.full((in_data.shape[3], nlabel), np.nan)

    for i, img in enumerate(np.moveaxis(in_data, 3, 0)):
        result[i, indices - 1] = mean(
            img, labels=labels.reshape(img.shape), index=indices
        )

    if output_coverage is True:
        return result, out_region_coverage
    else:
        return result


class ConnectivityMeasureInputSpec(BaseInterfaceInputSpec):
    in_file = File(
        desc="Image file(s) from where to extract the data", exists=True, mandatory=True
    )
    mask_file = File(desc="Mask file", exists=True, mandatory=True)
    atlas_file = File(
        desc="Atlas image file defining the connectivity ROIs",
        exists=True,
        mandatory=True,
    )

    background_label = traits.Int(desc="", default=0, usedefault=True)
    min_region_coverage = traits.Float(desc="", default=0.8, usedefault=True)


class ConnectivityMeasureOutputSpec(TraitedSpec):
    time_series = File(desc="Numpy text file with the timeseries matrix")
    covariance = File(desc="Numpy text file with the connectivity matrix")
    correlation = File(desc="Numpy text file with the connectivity matrix")
    region_coverage = traits.List(traits.Float)


class ConnectivityMeasure(BaseInterface):
    """
    Nipype interfaces to calculate connectivity measures using nilearn.
    Adapted from https://github.com/Neurita/pypes
    """

    input_spec = ConnectivityMeasureInputSpec
    output_spec = ConnectivityMeasureOutputSpec

    def _run_interface(self, runtime):
        self._time_series, self._region_coverage = mean_signals(
            self.inputs.in_file,
            self.inputs.atlas_file,
            output_coverage=True,
            mask_file=self.inputs.mask_file,
            background_label=self.inputs.background_label,
            min_region_coverage=self.inputs.min_region_coverage,
        )

        df: pd.DataFrame = pd.DataFrame(self._time_series)

        self._cov_mat = df.cov().values
        self._corr_mat = df.corr().values

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()

        argdict = dict(fmt="%.10f", delimiter="\t")

        time_series_file = op.abspath("timeseries.tsv")
        np.savetxt(time_series_file, self._time_series, **argdict)

        covariance_file = op.abspath("covariance.tsv")
        np.savetxt(covariance_file, self._cov_mat, **argdict)

        correlation_file = op.abspath("correlation.tsv")
        np.savetxt(correlation_file, self._corr_mat, **argdict)

        outputs["time_series"] = time_series_file
        outputs["covariance"] = covariance_file
        outputs["correlation"] = correlation_file

        outputs["region_coverage"] = self._region_coverage

        return outputs
