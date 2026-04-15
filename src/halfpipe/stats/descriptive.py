# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from typing import Literal, MutableSequence

import nibabel as nib
import numpy as np
import pandas as pd
from numpy import typing as npt

from ..design import ContrastMatrices
from ..utils.format import format_workflow
from .base import ModelAlgorithm, OutputFiles, VoxelResult, listwise_deletion


class Descriptive(ModelAlgorithm):
    model_outputs: list[str] = []
    contrast_outputs = ["mean", "std"]

    @staticmethod
    def voxel_calc(
        coordinate: tuple[int, ...],
        y: npt.NDArray[np.float64],
        z: npt.NDArray[np.float64],
        s: npt.NDArray[np.float64],
        cmatdict: ContrastMatrices,
    ) -> VoxelResult | None:
        # filtering for design matrix is already done
        # the nans that are left should be replaced with zeros
        z = np.nan_to_num(z)

        # remove observations with nan cope/varcope
        y, z, s = listwise_deletion(y, z, s)

        # make data frame
        zframe = pd.DataFrame(z)

        voxel_result: VoxelResult = defaultdict(dict)

        for name, cmat in cmatdict.items():
            if name.lower() == "intercept":
                continue

            voxel_result[name][coordinate] = dict(
                mean=cmat @ zframe.mean(),
                std=cmat @ zframe.std(),
            )

        return voxel_result

    @classmethod
    def write_outputs(
        cls,
        ref_img: nib.analyze.AnalyzeImage,
        cmatdict: ContrastMatrices,
        voxel_results: dict,
    ) -> OutputFiles:
        output_files: dict[str, MutableSequence[Literal[False] | str]] = dict()

        for output_name in cls.contrast_outputs:
            output_files[output_name] = [False] * len(cmatdict)

        for i, contrast_name in enumerate(cmatdict.keys()):  # cmatdict is ordered
            contrast_results = voxel_results[contrast_name]

            rdf = pd.DataFrame.from_records(contrast_results)

            for map_name, series in rdf.iterrows():
                assert isinstance(map_name, str)

                out_name = f"{map_name}_{i + 1}_{format_workflow(contrast_name)}"
                fname = cls.write_map(ref_img, out_name, series)

                output_name = map_name
                if output_name in output_files:
                    output_files[output_name][i] = str(fname)

        return output_files
