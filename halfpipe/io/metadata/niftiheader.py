# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional, Tuple, Dict

import re

import nibabel as nib
import pint

from ...utils import logger, splitext

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
        value = match.group("value")
        unit = groupdict.get("unit")

        varname = varname.lower()
        value = float(value)

        key = None

        if varname == "te":
            if unit is None:
                if value < 1:  # heuristic
                    unit = "s"
                else:
                    unit = "ms"

            key = "echo_time"

        elif varname == "tr":
            if unit is None:
                if value > 100:  # heuristic
                    unit = "ms"
                else:
                    unit = "s"

            key = "repetition_time"

        if key is not None:
            base_quantity = ureg(unit)
            assert isinstance(base_quantity, pint.Quantity)

            quantity = value * base_quantity

            descripdict[key] = quantity.m_as(ureg.seconds)

    return descripdict


class NiftiheaderLoader:
    cache = dict()

    @classmethod
    def load(cls, niftifile) -> Tuple[Optional[nib.Nifti1Header], Optional[Dict]]:
        if niftifile in cls.cache:
            return cls.cache[niftifile]

        _, ext = splitext(niftifile)

        if ext in [".mat"]:
            return None, None

        try:
            nbimg = nib.load(niftifile, mmap=False, keep_file_open=False)
        except Exception as e:
            logger.warning(f'Caught error loading file "{niftifile}"', e, exc_info=True)
            return None, None

        header = nbimg.header.copy()

        try:
            descripdict = parsedescrip(header)
        except Exception as e:
            logger.info(f'Could not parse nii file descrip for "{niftifile:s}: %s"', e, exc_info=True)
            descripdict = dict()

        cls.cache[niftifile] = header, descripdict
        return header, descripdict
