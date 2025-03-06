# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose, sqrt
from typing import Any, Iterable

import numpy as np
from nibabel.spatialimages import HeaderDataError
from numpy import typing as npt
from templateflow import api

from ...logging import logger
from ...model.file.base import File
from ...model.metadata import axis_codes, templates
from .base import Loader
from .direction import canonicalize_direction_code
from .niftiheader import NiftiheaderLoader
from .slicetiming import str_slice_timing

template_origin_sets = {
    template: set(tuple(value["origin"]) for value in api.get_metadata(template).get("res", dict()).values())
    for template in templates
}


class NiftiheaderMetadataLoader(Loader):
    cache: dict[str, Any] = dict()

    @staticmethod
    def load(niftifile):
        return NiftiheaderLoader.load(niftifile)

    def __init__(self, loader):
        self.loader = loader

    def fill(self, fileobj: File, key: str) -> bool:
        if key in fileobj.metadata:
            return True

        res = self.load(fileobj.path)

        if res is None or len(res) != 2:
            return False

        header, descripdict = res

        value: Any = None

        if header is None or descripdict is None:
            return False

        if hasattr(header, "get_dim_info"):
            _, _, slice_dim = header.get_dim_info()
        else:
            slice_dim = None

        try:
            if key == "slice_timing":
                n_slices = None

                if self.loader.fill(fileobj, "slice_encoding_direction"):
                    slice_encoding_direction = fileobj.metadata.get("slice_encoding_direction")
                    assert isinstance(slice_encoding_direction, str)

                    if slice_encoding_direction not in axis_codes:
                        slice_encoding_direction = canonicalize_direction_code(slice_encoding_direction, fileobj.path)

                    assert slice_encoding_direction in axis_codes, (
                        f'Unknown slice_encoding_direction "{slice_encoding_direction}"'
                    )

                    slice_dim = ["i", "j", "k"].index(slice_encoding_direction[0])
                    header.set_dim_info(slice=slice_dim)
                    n_slices = header.get_data_shape()[slice_dim]

                if not self.loader.fill(fileobj, "repetition_time"):
                    logger.info(f'Could not get repetition_time for "{fileobj.path}"')
                    return False
                repetition_time: float = fileobj.metadata["repetition_time"] * 1000  # needs to be in milliseconds

                nifti_slice_duration = header.get_slice_duration()
                if n_slices is not None and repetition_time is not None:
                    slice_duration = repetition_time / n_slices

                    if (
                        nifti_slice_duration > slice_duration  # too long
                        or nifti_slice_duration * n_slices
                        < repetition_time - 2 * slice_duration  # too short with fudge factor
                    ):
                        logger.info(
                            f"Image file header entry slice_duration ({nifti_slice_duration:f} ms) is "
                            f"inconsistent with repetition_time / n_slices ({slice_duration:f} ms) "
                            f'for file "{fileobj.path}"'
                        )
                        header.set_slice_duration(slice_duration)
                    if isclose(nifti_slice_duration, 0.0):
                        header.set_slice_duration(slice_duration)
                nifti_slice_duration = header.get_slice_duration()

                assert n_slices is not None

                slice_timing_code = fileobj.metadata.get("slice_timing_code")
                if slice_timing_code is None:
                    slice_times: Iterable[float] = header.get_slice_times()  # type: ignore
                else:
                    slice_times = str_slice_timing(slice_timing_code, n_slices, nifti_slice_duration)
                slice_times = [s / 1000.0 for s in slice_times]  # need to be in seconds
                if not all(isclose(slice_time, 0.0) for slice_time in slice_times):
                    value = slice_times

            elif key == "slice_encoding_direction":
                if slice_dim is not None:
                    value = ["i", "j", "k"][slice_dim]

            elif key == "repetition_time":
                if "repetition_time" in descripdict:
                    value = descripdict["repetition_time"]
                else:
                    zooms = header.get_zooms()

                    if zooms is None or len(zooms) != 4:
                        logger.info(f'Missing repetition_time in image file header zooms "{zooms}"')
                        return False

                    repetition_time = float(zooms[3])

                    units = header.get_xyzt_units()
                    if units is not None and len(units) == 2:
                        _, t_unit = units

                        if t_unit == "msec":
                            repetition_time /= 1e3
                        elif t_unit == "usec":
                            repetition_time /= 1e6
                        elif t_unit != "sec":
                            logger.info(
                                f'Unknown repetition_time units "{t_unit}" specified. '
                                f'Assuming {repetition_time:f} seconds for "{fileobj.path}"'
                            )
                    else:
                        logger.info(
                            f'Missing units for repetition_time. Assuming {repetition_time:f} seconds for "{fileobj.path}"'
                        )

                    value = repetition_time

            elif key == "echo_time":
                if "echo_time" in descripdict:
                    value = descripdict["echo_time"]

            elif key == "space":
                affine = header.get_best_affine()
                if not isinstance(affine, np.ndarray):
                    return False
                origin: npt.NDArray[np.float64] = affine[0:3, 3]
                for name, template_origin_set in template_origin_sets.items():
                    for template_origin in template_origin_set:
                        o: npt.NDArray[np.float64] = np.array(template_origin)

                        # use squared values as we don't care about orientation
                        if sqrt(np.square(o - origin).mean()) < 1:
                            value = name
                            break

        except HeaderDataError:
            return False

        if value is None:
            return False

        fileobj.metadata[key] = value
        return True
