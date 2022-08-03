# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nibabel.nifti1 import Nifti1Header

from ..ingest.bids import get_file_metadata
from ..ingest.metadata.direction import get_axcodes_set
from ..ingest.metadata.niftiheader import NiftiheaderLoader
from ..model.setting import BaseSettingSchema


def collect_metadata(database, source_file, setting) -> dict:
    metadata = dict(setting=BaseSettingSchema().dump(setting))

    metadata.update(get_file_metadata(database, source_file))

    header, _ = NiftiheaderLoader.load(source_file)
    assert isinstance(header, Nifti1Header)

    zooms = list(map(float, header.get_zooms()))
    assert all(isinstance(z, float) for z in zooms)
    metadata["acquisition_voxel_size"] = tuple(zooms[:3])

    data_shape = header.get_data_shape()
    assert len(data_shape) == 4
    metadata["acquisition_volume_shape"] = tuple(data_shape[:3])
    metadata["number_of_volumes"] = int(data_shape[3])

    (axcodes,) = get_axcodes_set(source_file)
    axcode_str = "".join(axcodes)
    metadata["acquisition_orientation"] = axcode_str

    return metadata
