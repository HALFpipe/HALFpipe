# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging

import numpy as np
import nibabel as nib

from .niftiheader import NiftiheaderLoader

from .direction import canonicalize_direction_code
from .slicetiming import str_slice_timing
from ...model import axis_codes


class NiftiheaderMetadataLoader:
    cache = dict()

    @classmethod
    def load(cls, niftifile):
        return NiftiheaderLoader.load(niftifile)

    def fill(self, fileobj, key):
        if key in fileobj.metadata:
            return True

        res = self.load(fileobj.path)

        if res is None or len(res) != 2:
            return False

        header, descripdict = res

        value = None

        _, _, slice_dim = header.get_dim_info()

        if key == "slice_timing":
            try:
                n_slices = None
                if self.fill(fileobj, "slice_encoding_direction"):
                    slice_encoding_direction = fileobj.metadata.get("slice_encoding_direction")
                    if slice_encoding_direction not in axis_codes:
                        slice_encoding_direction = canonicalize_direction_code(
                            slice_encoding_direction, fileobj.path
                        )
                    assert slice_encoding_direction in axis_codes
                    slice_dim = ["i", "j", "k"].index(
                        slice_encoding_direction[0]
                    )
                    header.set_dim_info(slice=slice_dim)
                    n_slices = header.get_data_shape()[slice_dim]

                repetition_time = None
                if self.fill(fileobj, "repetition_time"):
                    repetition_time = fileobj.metadata.get("repetition_time") * 1000

                nifti_slice_duration = header.get_slice_duration()
                if n_slices is not None and repetition_time is not None:
                    slice_duration = repetition_time / n_slices
                    if nifti_slice_duration * n_slices < repetition_time - 2 * slice_duration:  # fudge factor
                        logging.getLogger("halfpipe").warning(
                            f'Unexpected nifti slice_duration = {nifti_slice_duration:f} for file "{fileobj.path}"\n'
                            f"nifti slice_duration * n_slices ({nifti_slice_duration*n_slices:f} ms) "
                            f"is much smaller than repetition_time ({repetition_time:f} ms), "
                            "even though we expect them to be approximately equal\n"
                            f"Setting slice_duration to repetition_time / n_slices = {slice_duration:f} ms"
                        )
                        header.set_slice_duration(slice_duration)
                    if np.isclose(nifti_slice_duration, 0.0):
                        header.set_slice_duration(slice_duration)
                nifti_slice_duration = header.get_slice_duration()

                slice_timing_code = fileobj.metadata.get("slice_timing_code")
                if slice_timing_code is None:
                    slice_times = header.get_slice_times()
                    slice_times = [s / 1000.0 for s in slice_times]  # need to be in seconds
                    if not np.allclose(slice_times, 0.0):
                        value = slice_times
                else:
                    value = str_slice_timing(slice_timing_code, n_slices, nifti_slice_duration)
            except nib.spatialimages.HeaderDataError:
                return False

        elif key == "slice_encoding_direction" and slice_dim is not None:
            value = ["i", "j", "k"][slice_dim]

        elif key == "repetition_time":
            if "repetition_time" in descripdict:
                value = descripdict["repetition_time"]
            else:
                value = float(header.get_zooms()[3])

        elif key == "echo_time":
            if "echo_time" in descripdict:
                value = descripdict["echo_time"]

        elif key == "space":
            spaceorigins = {
                "MNI152NLin2009cAsym": np.array([-96.0, -132.0, -78.0]),
                "MNI152NLin6Asym": np.array([-91.0, -126.0, -72.0]),
            }
            origin = np.array([header["qoffset_x"], header["qoffset_y"], header["qoffset_z"]])
            for name, o in spaceorigins.items():
                delta = np.abs(o) - np.abs(
                    origin
                )  # use absolute values as we don't care about orientation
                if np.sqrt(np.square(delta).mean()) < 1:
                    value = name
                    break

        if value is None:
            return False

        fileobj.metadata[key] = value
        return True
