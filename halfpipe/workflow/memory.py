# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Tuple

from nipype.pipeline import engine as pe
from templateflow.api import get as get_template

import pint

from .constants import constants
from ..io.metadata.niftiheader import NiftiheaderLoader

ureg = pint.UnitRegistry()


class MemoryCalculator:
    min_gb: float = 0.3  # we assume that any command needs a few hundred megabytes

    def __init__(self, database=None, bold_file=None, bold_shape=[72, 72, 72], bold_tlen=200):

        if database is not None:
            bold_file = next(iter(
                database.get(datatype="func", suffix="bold")
            ))

        if bold_file is not None:
            header, _ = NiftiheaderLoader.load(bold_file)
            if header is not None:
                bold_shape = header.get_data_shape()

        t = 1
        for n in bold_shape[3:]:
            t *= n

        if t == 1:
            t = bold_tlen

        x, y, z = bold_shape[:3]
        self.volume_gb, self.series_gb = self.calc_bold_gb((x, y, z, t))

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
        self.volume_std_gb, self.series_std_gb = self.calc_bold_gb((x, y, z, t))

    def calc_bold_gb(self, shape: Tuple[int, int, int, int]) -> Tuple[float, float]:
        x, y, z, t = shape
        volume_bytes = ureg.Quantity(x * y * z * 8, ureg.bytes)

        volume_gb: float = volume_bytes.to(ureg.gigabytes).m
        series_gb: float = volume_gb * t

        if volume_gb < self.min_gb:
            volume_gb = volume_gb

        if series_gb < self.min_gb:
            series_gb = self.min_gb

        return volume_gb, series_gb

    def __hash__(self):
        return hash(
            (
                self.volume_gb,
                self.series_gb,
                self.volume_std_gb,
                self.series_std_gb,
                self.min_gb,
            )
        )


def patch_mem_gb(node: pe.Node, omp_nthreads: int, memcalc: MemoryCalculator):
    name = node.fullname
    assert isinstance(name, str)

    # reduce

    if name.endswith("bold_std_trans_wf.bold_to_std_transform"):
        node._mem_gb = 50 * memcalc.volume_std_gb * omp_nthreads

    if name.endswith("bold_t1_trans_wf.bold_to_t1w_transform"):
        node._mem_gb = 20 * memcalc.volume_std_gb * omp_nthreads

    if name.endswith("bold_bold_trans_wf.bold_transform"):
        node._mem_gb = 20 * memcalc.volume_gb * omp_nthreads

    # increase

    if name.endswith("bold_stc_wf.slice_timing_correction"):
        node._mem_gb = memcalc.series_gb

    if name.endswith("carpetplot_wf.conf_plot"):
        node._mem_gb = 1.5 * memcalc.series_std_gb

    if name.endswith("bold_std_trans_wf.merge"):
        node._mem_gb = memcalc.series_std_gb

    if name.endswith("bold_confounds_wf.fdisp"):
        node._mem_gb = memcalc.min_gb

    if name.endswith("ica_aroma_wf.smooth"):
        node._mem_gb = 1.5 * memcalc.series_std_gb

    if name.endswith("ica_aroma_wf.ica_aroma"):
        node._mem_gb = 0.5 * memcalc.series_std_gb

    if any(
        name.endswith(s)
        for s in [
            "ica_aroma_wf.melodic",
            "ica_aroma_wf.calc_bold_mean",
            "ica_aroma_wf.calc_median_val",
        ]
    ):
        node._mem_gb = 1.0 * memcalc.series_std_gb

    if node.mem_gb < memcalc.min_gb:
        node._mem_gb = memcalc.min_gb
