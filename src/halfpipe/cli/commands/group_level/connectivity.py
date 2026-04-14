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
    images = result["images"]

    if "effect" in images and "variance" in images:
        effect = np.loadtxt(images["effect"])
        variance = np.loadtxt(images["variance"])
    elif "timeseries" in images:
        timeseries = np.loadtxt(images.pop("timeseries"))
        effect, variance = xdf(timeseries.transpose())
    else:
        return result

    tags_str = "_".join(f"{key}-{value}" for key in entities[::-1] if (value := result["tags"].get(key)) is not None)

    effect_path = Path.cwd() / f"{tags_str}_effect.nii.gz"
    nib.nifti1.save(nib.nifti1.Nifti1Image(effect, affine=np.eye(4)), effect_path)
    images["effect"] = effect_path

    variance_path = Path.cwd() / f"{tags_str}_variance.nii.gz"
    nib.nifti1.save(nib.nifti1.Nifti1Image(variance, affine=np.eye(4)), variance_path)
    images["variance"] = variance_path

    mask_path = Path.cwd() / f"{tags_str}_mask.nii.gz"
    mask = np.logical_and(np.isfinite(effect), np.isfinite(variance)).astype(np.int8)
    nib.nifti1.save(nib.nifti1.Nifti1Image(mask, affine=np.eye(4)), mask_path)
    images["mask"] = mask_path

    return result


def apply_xdf(design_base: DesignBase, num_threads: int) -> None:
    connectivity_results: list[ResultDict] = list()
    other_results: list[ResultDict] = list()
    for result in design_base.results:
        if "timeseries" in result["images"]:
            connectivity_results.append(result)
        else:
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
