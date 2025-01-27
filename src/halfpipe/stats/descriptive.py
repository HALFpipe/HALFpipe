# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from typing import Dict, List, Literal, Optional, Tuple, Union

import nibabel as nib
import numpy as np
import pandas as pd

from ..utils.format import format_workflow
from .base import ModelAlgorithm, listwise_deletion


class Descriptive(ModelAlgorithm):
    model_outputs: List[str] = []
    contrast_outputs = ["mean", "std"]

    @staticmethod
    def voxel_calc(
        coordinate: Tuple[int, int, int],
        y: np.ndarray,
        z: np.ndarray,
        s: np.ndarray,
        cmatdict: dict,
    ) -> Optional[Dict]:
        # filtering for design matrix is already done
        # the nans that are left should be replaced with zeros
        z = np.nan_to_num(z)

        # remove observations with nan cope/varcope
        y, z, s = listwise_deletion(y, z, s)

        # make data frame
        zframe = pd.DataFrame(z)

        voxel_result: Dict[str, Dict[Tuple[int, int, int], Dict[str, float]]] = defaultdict(dict)

        for name, cmat in cmatdict.items():
            if name.lower() == "intercept":
                continue

            voxel_result[name][coordinate] = dict(
                mean=cmat @ zframe.mean(),
                std=cmat @ zframe.std(),
            )

        return voxel_result

    @classmethod
    def write_outputs(cls, ref_img: nib.analyze.AnalyzeImage, cmatdict: Dict, voxel_results: Dict) -> Dict:
        output_files: Dict[str, List[Union[Literal[False], str]]] = dict()

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
