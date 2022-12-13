# -*- coding: utf-8 -*-
import subprocess

import nibabel as nib
import numpy as np
import pytest

from ..niftiheader import parse_descrip  # noqa


@pytest.mark.parametrize()
def dump_header(img_fname, out_fname):
    """Use fslhd to dump an image header to a text file
    Parameters
    ----------
    img_fname : str
        Filename of the image to use.
    out_fname : str
        Filename to save the header to.
    """
    with open(out_fname, "w") as fid:
        subprocess.check_call(["fslhd", "-x", img_fname], stdout=fid)


def test_NiftiheaderLoader_parse_descrip(tmp_path):
    size = (2, 3, 4)

    # out_fname = str(tmp_path / "text.txt")
    fname = str(tmp_path / "testdata.nii")

    nib.Nifti1Image(np.zeros(size), np.eye(4)).to_filename(fname)
    img: nib.Nifti1Image = nib.load(fname)
    # hdr: nib.Nifti1Header = img.header
    img.header["descrip"] = "TE=30"  # do it like this

    # hdr: nib.Nifti1Header = img.header
    # image.header["descrip"]
    # nib.save(fname)
    # dump_header(img_fname=fname, out_fname=out_fname)

    descrip_dict = parse_descrip(header=img.header)
    print("TEST", descrip_dict.keys())
