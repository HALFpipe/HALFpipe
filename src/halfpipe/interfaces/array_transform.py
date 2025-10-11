# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import prod
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn.image import new_img_like
from nipype.interfaces.base import File, SimpleInterface, TraitedSpec, isdefined, traits
from numpy import typing as npt

from ..ingest.spreadsheet import read_spreadsheet
from ..utils.path import split_ext


class ArrayTransformInputSpec(TraitedSpec):
    in_file = File(desc="File to filter", exists=True, mandatory=True)
    mask = File(desc="mask to use for volumes", exists=True)

    write_header = traits.Bool(default_value=True, usedefault=True)


class ArrayTransformOutputSpec(TraitedSpec):
    out_file = File()


class ArrayTransform(SimpleInterface):
    """
    Interface that takes any kind of array input and applies a function to it
    """

    input_spec = ArrayTransformInputSpec
    output_spec = ArrayTransformOutputSpec

    suffix = "transformed"

    def _transform(self, array: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        raise NotImplementedError

    def _load(self, in_file: Path | str, mask_file: Path | str | None = None) -> npt.NDArray[np.float64]:
        stem, ext = split_ext(in_file)
        self.stem, self.extension = stem, ext

        if mask_file is None:
            mask_file = self.inputs.mask

        self.mask = None

        if ext in [".nii", ".nii.gz"]:
            image = nib.nifti1.load(in_file)
            self.image = image

            array_proxy = image.dataobj

            ndim = image.ndim
            if image.ndim == 3:
                array_proxy.reshape = (*image.shape, 1)
            elif ndim == 4:
                pass
            else:
                raise ValueError(f'Unexpect number of dimensions {ndim:d} in "{in_file}"')

            volume_shape = array_proxy.shape[:3]
            voxel_count = prod(volume_shape)
            volume_count = array_proxy.shape[3]

            if isdefined(mask_file) and isinstance(mask_file, str) and Path(mask_file).is_file():
                mask_image = nib.funcs.squeeze_image(nib.nifti1.load(mask_file))

                if mask_image.ndim != 3:
                    raise ValueError(f'Expecting a single volume for mask file "{mask_file}"')
                if image.affine is not None:
                    if not np.allclose(mask_image.affine, image.affine):
                        raise ValueError(f'Affine mismatch between "{in_file}" and "{mask_file}"')

                mask = mask_image.get_fdata(dtype=np.float64)
                binary_mask = np.logical_not(np.logical_or(mask <= 0, np.isclose(mask, 0, atol=1e-2)))

                self.mask = binary_mask
                voxel_count = np.count_nonzero(binary_mask)

            array = np.zeros((volume_count, voxel_count))

            for i in range(volume_count):
                volume_data = array_proxy[..., i]

                if self.mask is not None:
                    array[i, :] = volume_data[self.mask]
                else:
                    array[i, :] = volume_data.ravel()

        else:  # a text file
            data_frame = read_spreadsheet(in_file)
            self.data_frame = data_frame
            array = data_frame.to_numpy().astype(np.float64)

        return array

    def _dump(self, array2: npt.NDArray[np.float64]) -> str:
        stem, extension = self.stem, self.extension
        output_path = Path(f"{stem}_{self.suffix}{extension}").resolve()

        if extension in [".nii", ".nii.gz"]:
            image = self.image

            if self.mask is not None:
                volume_count = array2.shape[0]
                output_array = np.zeros((*image.shape[:3], volume_count))
                output_array[self.mask, :] = array2.transpose()
            else:
                output_array = array2.transpose().reshape((*image.shape[:3], -1))

            # squeeze time axis if we are outputting a single volume
            if output_array.shape[3] == 1:
                output_array = np.squeeze(output_array, axis=3)

            output_image = new_img_like(image, output_array, copy_header=True)
            assert isinstance(output_image.header, nib.nifti1.Nifti1Header)

            output_image.header.set_data_dtype(np.float64)
            nib.loadsave.save(output_image, output_path)
        else:
            header = True
            if (
                hasattr(self.inputs, "write_header")
                and isdefined(self.inputs.write_header)
                and self.inputs.write_header is False
            ):
                header = False

            output_data_frame = pd.DataFrame(data=array2, columns=self.data_frame.columns)
            output_data_frame.to_csv(
                output_path,
                sep="\t",
                index=False,
                na_rep="n/a",
                header=header,
            )

        return str(output_path)

    def _run_interface(self, runtime):
        self._merged_file = None

        in_file = self.inputs.in_file

        array = self._transform(
            self._load(in_file)  # observations x variables
        )

        out_file = self._dump(array)
        self._results["out_file"] = out_file

        return runtime
