# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from contextlib import chdir
from multiprocessing import cpu_count
from pathlib import Path

from nipype.interfaces import fsl
from tqdm.auto import tqdm

from halfpipe.result.base import ResultDict

from ....design import intercept_only_design
from ....interfaces.image_maths.merge import merge, merge_mask
from ....logging import logger
from ....result.aggregate import aggregate_results, summarize_metadata
from ....utils.hash import b32_digest
from ....utils.multiprocessing import Pool
from .base import aliases
from .design import DesignBase


def apply_aggregate(
    design: DesignBase,
    n_procs: int = cpu_count(),
) -> None:
    if design.aggregate is None:
        return

    results = design.results
    for key in design.aggregate:
        results, bypass = aggregate_results(results, key)

        logger.info(f'Will run {len(results):d} models at level "{key}"')
        with Pool(processes=n_procs) as pool:
            results = list(
                tqdm(
                    pool.imap_unordered(map_fixed_effects_aggregate, results),
                    total=len(results),
                    desc=f'aggregate "{key}"',
                )
            )

        results.extend(bypass)
        results = [summarize_metadata(result) for result in results]
    # Set in design object
    design.results = results


def map_fixed_effects_aggregate(result: ResultDict) -> ResultDict:
    key = b32_digest(result)[:8]

    model_directory = Path.cwd() / f"model-{key}"
    model_directory.mkdir(exist_ok=False, parents=True)

    tags = {
        key: value for key, value in result["tags"].items() if isinstance(value, str)
    }  # filter out list fields

    images = result["images"]
    result["images"] = dict()

    for from_key, to_key in aliases.items():
        if from_key in images:
            images[to_key] = images.pop(from_key)

    cope_files = images.pop("effect")
    var_cope_files = images.pop("variance")
    mask_files = images.pop("mask")

    with chdir(model_directory):
        cope_file = merge(cope_files, "t")
        var_cope_file = merge(var_cope_files, "t")
        mask_file = merge_mask(mask_files)

        n = len(cope_files)
        (regressors, contrasts, _, _) = intercept_only_design(n)
        multiple_regress_design = fsl.MultipleRegressDesign(
            regressors=regressors,
            contrasts=contrasts,
        ).run()
        assert multiple_regress_design.outputs is not None

        flameo = fsl.FLAMEO(
            cope_file=cope_file,
            var_cope_file=var_cope_file,
            mask_file=mask_file,
            run_mode="fe",
            design_file=multiple_regress_design.outputs.design_mat,
            t_con_file=multiple_regress_design.outputs.design_con,
            cov_split_file=multiple_regress_design.outputs.design_grp,
        ).run()  # type: ignore
        assert flameo.outputs is not None

    cope_file = flameo.outputs.copes
    var_cope_file = flameo.outputs.var_copes

    images = dict(
        effect=cope_file,
        variance=var_cope_file,
        mask=mask_file,
    )

    result["tags"] = tags
    result["images"] = images

    return result
