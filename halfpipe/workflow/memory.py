# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Tuple, NamedTuple, Union

from pathlib import Path

import pint

from nipype.pipeline import engine as pe
from templateflow.api import get as get_template
from fmriprep import config

from .constants import constants
from ..io.metadata.niftiheader import NiftiheaderLoader

ureg = pint.UnitRegistry()


class MemoryCalculator(NamedTuple):
    volume_gb: float
    series_gb: float

    volume_std_gb: float
    series_std_gb: float

    min_gb: float = 0.3  # we assume that any command needs a few hundred megabytes

    @classmethod
    def from_bold_shape(cls, x: int = 72, y: int = 72, z: int = 72, t: int = 200):
        volume_gb, series_gb = cls.calc_bold_gb((x, y, z, t))

        reference_file = get_template(
            constants.reference_space,
            resolution=constants.reference_res,
            desc="brain",
            suffix="mask",
        )
        header, _ = NiftiheaderLoader.load(reference_file)
        assert header is not None
        reference_shape = header.get_data_shape()

        x, y, z = reference_shape[:3]
        volume_std_gb, series_std_gb = cls.calc_bold_gb((x, y, z, t))

        return MemoryCalculator(
            volume_gb=volume_gb,
            series_gb=series_gb,
            volume_std_gb=volume_std_gb,
            series_std_gb=series_std_gb,
        )

    @classmethod
    def default(cls):
        return MemoryCalculator.from_bold_shape()

    @classmethod
    def from_bold_file(cls, bold_file: Union[str, Path]):
        header, _ = NiftiheaderLoader.load(bold_file)
        if header is not None:
            bold_shape = header.get_data_shape()

            t = 1
            for n in bold_shape[3:]:
                t *= n

            x, y, z = bold_shape[:3]

            if t == 1:
                return cls.from_bold_shape(x=x, y=y, z=z)

            return cls.from_bold_shape(x=x, y=y, z=z, t=t)

        return cls.default()

    @classmethod
    def calc_bold_gb(cls, shape: Tuple[int, int, int, int]) -> Tuple[float, float]:
        x, y, z, t = shape
        volume_bytes = ureg.Quantity(x * y * z * 8, ureg.bytes)

        volume_gb: float = volume_bytes.to(ureg.gigabytes).m
        series_gb: float = volume_gb * t

        min_gb: float = cls._field_defaults["min_gb"]

        volume_gb = max(min_gb, volume_gb)
        series_gb = max(min_gb, series_gb)

        return round(volume_gb, 3), round(series_gb, 3)


def patch_mem_gb(node: pe.Node, memcalc: MemoryCalculator):
    name = node.fullname
    assert isinstance(name, str)

    omp_nthreads = config.nipype.omp_nthreads
    assert isinstance(omp_nthreads, int)

    if name.endswith("bold_std_trans_wf.bold_to_std_transform"):
        node._mem_gb = 2 * memcalc.volume_std_gb * omp_nthreads

    if name.endswith("bold_t1_trans_wf.bold_to_t1w_transform"):
        node._mem_gb = memcalc.volume_std_gb * omp_nthreads

    if name.endswith("bold_std_trans_wf.merge"):
        node._mem_gb = 0.75 * memcalc.series_std_gb

    if name.endswith("bold_confounds_wf.fdisp"):
        node._mem_gb = memcalc.min_gb

    if name.endswith("ica_aroma_wf.smooth"):
        node._mem_gb = 1.5 * memcalc.series_std_gb

    if name.endswith("ica_aroma_wf.ica_aroma"):
        node._mem_gb = 0.5 * memcalc.series_std_gb

    if any(
        name.endswith(s)
        for s in [
            "bold_stc_wf.slice_timing_correction",
            "bold_hmc_wf.mcflirt",
            "bold_bold_trans_wf.bold_transform",
            "bold_bold_trans_wf.merge",
        ]
    ):
        node._mem_gb = memcalc.series_gb

    if any(
        name.endswith(s)
        for s in [
            "ica_aroma_wf.melodic",
            "ica_aroma_wf.calc_bold_mean",
            "ica_aroma_wf.calc_median_val",
        ]
    ):
        node._mem_gb = memcalc.series_std_gb

    if any(
        name.endswith(s)
        for s in [
            "carpetplot_wf.conf_plot",
            "bold_confounds_wf.rois_plot",
            "bold_confounds_wf.signals",
            "bold_confounds_wf.tcompcor",
        ]
    ):
        node._mem_gb = 2 * memcalc.series_std_gb

    if node.mem_gb < memcalc.min_gb:
        node._mem_gb = memcalc.min_gb
