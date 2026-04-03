from pathlib import Path

import nibabel as nib
import numpy as np
from tqdm import tqdm

from halfpipe.cli.commands.group_level.design import DesignBase
from halfpipe.model.tags.schema import entities
from halfpipe.result.base import ResultDict
from halfpipe.utils.multiprocessing import make_pool_or_null_context
from halfpipe.xdf import xdf


def inner(result: ResultDict) -> ResultDict:
    if "timeseries" not in result["images"]:
        return result

    timeseries = np.loadtxt(result["images"].pop("timeseries"))

    effect, variance = xdf(timeseries.transpose())

    tags_str = "_".join(f"{key}-{value}" for key in entities[::-1] if (value := result["tags"].get(key)) is not None)

    effect_path = Path.cwd() / f"{tags_str}_effect.nii.gz"
    image = nib.nifti1.Nifti1Image(np.atleast_3d(effect), affine=np.eye(4))
    nib.nifti1.save(image, effect_path)
    result["images"]["effect"] = effect_path

    variance_path = Path.cwd() / f"{tags_str}_variance.nii.gz"
    image = nib.nifti1.Nifti1Image(np.atleast_3d(variance), affine=np.eye(4))
    nib.nifti1.save(image, variance_path)
    result["images"]["variance"] = variance_path

    return result


def apply_xdf(design_base: DesignBase, num_threads: int) -> None:
    connectivity_results: list[ResultDict] = list()
    other_results: list[ResultDict] = list()
    for result in design_base.results:
        if "timeseries" in result["images"]:
            result["metadata"]["is_connectivity"] = True
            connectivity_results.append(result)
        else:
            result["metadata"]["is_connectivity"] = False
            other_results.append(result)

    if connectivity_results:
        cm, iterator = make_pool_or_null_context(
            connectivity_results,
            callable=inner,
            num_threads=num_threads,
        )
        with cm:
            connectivity_results = list(
                tqdm(
                    iterator,
                    total=len(connectivity_results),
                    desc="loading connectivity",
                    unit="matrices",
                )
            )

    design_base.results = connectivity_results + other_results
