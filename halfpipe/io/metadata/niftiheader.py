# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
import logging

import numpy as np
import nibabel as nib
import pint

ureg = pint.UnitRegistry()

descripvar = re.compile(
    r"(?P<varname>\w+)=(?P<value>(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)(?P<unit>s|ms|us)?"
)


def parsedescrip(header):
    descripdict = dict()

    descrip = header.get("descrip").tolist().decode()
    for match in descripvar.finditer(descrip):
        groupdict = match.groupdict()

        varname = groupdict.get("varname")
        value = groupdict.get("value")
        unit = groupdict.get("unit")

        varname = varname.lower()
        value = float(value)

        if varname == "te":
            if unit is None:
                if value < 1:  # heuristic
                    unit = "s"
                else:
                    unit = "ms"

            quantity = value * ureg(unit)

            descripdict["echo_time"] = quantity.m_as(ureg.seconds)
        elif varname == "tr":
            if unit is None:
                if value > 100:  # heuristic
                    unit = "ms"
                else:
                    unit = "s"

            quantity = value * ureg(unit)

            descripdict["repetition_time"] = quantity.m_as(ureg.seconds)

    return descripdict


class NiftiheaderMetadataLoader:
    cache = dict()

    @classmethod
    def load(cls, niftifile):
        if niftifile in cls.cache:
            return cls.cache[niftifile]

        try:
            nbimg = nib.load(niftifile, mmap=False, keep_file_open=False)
        except Exception:
            return

        header = nbimg.header.copy()
        descripdict = parsedescrip(header)

        cls.cache[niftifile] = header, descripdict
        return header, descripdict

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
                    slice_dim = ["i", "j", "k"].index(
                        fileobj.metadata.get("slice_encoding_direction")[0]
                    )
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
                slice_times = header.get_slice_times()
                slice_times = [s / 1000.0 for s in slice_times]  # need to be in seconds
                if not np.allclose(slice_times, 0.0):
                    value = slice_times
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
