# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Any

import nibabel as nib
import numpy as np
import pandas as pd
from nipype.interfaces.base import (
    DynamicTraitedSpec,
    File,
    SimpleInterface,
    TraitedSpec,
    isdefined,
    traits,
)
from nipype.interfaces.base.support import Bunch
from nipype.interfaces.io import IOBase, add_traits

from ... import __version__ as halfpipe_version
from ...ingest.spreadsheet import read_spreadsheet
from ..connectivity import mean_signals


class CalcMeanInputSpec(TraitedSpec):
    in_file = File(exists=True, mandatory=True)
    mask = File(exists=True)
    parcellation = File(exists=True)
    dseg = File(exists=True)

    vals = traits.Dict(traits.Str(), traits.Any())
    key = traits.Str()


class CalcMeanOutputSpec(TraitedSpec):
    mean = traits.Either(traits.Float(), traits.List(traits.Float()))
    vals = traits.Dict(traits.Str(), traits.Any())


class CalcMean(SimpleInterface):
    input_spec = CalcMeanInputSpec
    output_spec = CalcMeanOutputSpec

    def _run_interface(self, runtime: Bunch) -> Bunch:
        in_img = nib.nifti1.load(self.inputs.in_file)
        mask_img: nib.analyze.AnalyzeImage | None = None
        if isdefined(self.inputs.mask):
            mask_img = nib.nifti1.load(self.inputs.mask)

        if isdefined(self.inputs.dseg):  # get grey matter only
            atlas_img = nib.nifti1.load(self.inputs.dseg)
            dseg_mean_signals = mean_signals(
                in_img,
                atlas_img,
                mask_image=mask_img,
            )
            _, gm_mean, _ = np.ravel(dseg_mean_signals).tolist()
            self._results["mean"] = float(gm_mean)

        elif isdefined(self.inputs.parcellation):
            atlas_img = nib.nifti1.load(self.inputs.parcellation)
            parc_mean_signals = mean_signals(in_img, atlas_img, mask_image=mask_img)
            parc_mean_signals_list = list(map(float, np.ravel(parc_mean_signals).tolist()))
            self._results["mean"] = parc_mean_signals_list

        elif mask_img is not None:
            mean = mean_signals(in_img, mask_img)
            self._results["mean"] = float(mean[0].item())

        vals: dict[str, Any] = dict()
        self._results["vals"] = vals
        if isdefined(self.inputs.vals):
            vals.update(self.inputs.vals)
        if isdefined(self.inputs.key):
            vals[self.inputs.key] = self._results["mean"]
        return runtime


class UpdateValsInputSpec(DynamicTraitedSpec):
    vals = traits.Dict(traits.Str(), traits.Any())
    confounds_file = File(exists=True)
    confounds_selected = File(exists=True)
    aroma_column_names = traits.List(traits.Str(), exists=True)
    fd_thres = traits.Float()


class UpdateValsOutputSpec(TraitedSpec):
    vals = traits.Dict(traits.Str(), traits.Any())


class UpdateVals(IOBase):
    input_spec = UpdateValsInputSpec
    output_spec = UpdateValsOutputSpec

    def __init__(self, fields: list | None = None, **inputs):
        super().__init__(**inputs)

        self.fields = [] if fields is None else fields
        add_traits(self.inputs, [*self.fields])

    def _list_outputs(self):
        outputs = self._outputs()
        assert outputs is not None
        outputs = outputs.get()

        vals: dict[str, Any] = dict(confound_regressors=list(), halfpipe_version=halfpipe_version)

        if isdefined(self.inputs.vals):
            vals.update(self.inputs.vals)

        confounds_file = self.inputs.confounds_file
        if isdefined(confounds_file):
            data_frame = pd.read_csv(
                confounds_file,
                sep="\t",
                index_col=None,
                dtype=np.float64,
                na_filter=True,
                na_values="n/a",
            )
            assert isinstance(data_frame, pd.DataFrame)

            framewise_displacement = data_frame["framewise_displacement"].dropna()

            vals["fd_mean"] = float(framewise_displacement.mean())
            vals["fd_max"] = float(framewise_displacement.max())

            if isdefined(self.inputs.fd_thres):
                fd_prop = float((framewise_displacement > self.inputs.fd_thres).mean())
                vals["fd_perc"] = fd_prop * 100  # rescale to percent

        confounds_selected = self.inputs.confounds_selected
        if isdefined(confounds_selected):
            data_frame = read_spreadsheet(confounds_selected)
            vals["confound_regressors"].extend(data_frame.columns)

        if isdefined(self.inputs.aroma_column_names):
            aroma_column_names = self.inputs.aroma_column_names
            is_noise_component = [aroma_column_name.startswith("aroma_noise") for aroma_column_name in aroma_column_names]
            vals["aroma_noise_frac"] = float(np.array(is_noise_component).astype(float).mean())
            vals["confound_regressors"].extend(
                aroma_column_name for aroma_column_name in aroma_column_names if aroma_column_name.startswith("aroma_noise")
            )

        for field in self.fields:
            value = getattr(self.inputs, field, None)
            if isdefined(value):
                vals[field] = value

        outputs["vals"] = vals

        return outputs
