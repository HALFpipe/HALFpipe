# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from contextlib import chdir
from pathlib import Path

from nipype.interfaces import fsl
from tqdm.auto import tqdm

from ....design import intercept_only_design
from ....interfaces.image_maths.merge import merge, merge_mask
from ....logging import logger
from ....result.aggregate import aggregate_results, summarize_metadata
from ....result.base import ResultDict
from ....utils.hash import b32_digest
from ....utils.multiprocessing import make_pool_or_null_context
from .base import aliases
from .design import DesignBase


def apply_aggregate(
    design: DesignBase,
    num_threads: int,
) -> None:
    if design.aggregate is None:
        return

    results = design.results
    for key in design.aggregate:
        results, other_results = aggregate_results(results, key)

        logger.info(f'Will run {len(results):d} models at level "{key}"')
        cm, iterator = make_pool_or_null_context(
            results,
            callable=map_fixed_effects_aggregate,
            num_threads=num_threads,
        )
        with cm:
            results = list(
                tqdm(
                    iterator,
                    total=len(results),
                    desc=f'aggregate "{key}"',
                )
            )

        results.extend(other_results)
        for result in results:
            # Remove list fields
            result["tags"] = {key: value for key, value in result["tags"].items() if isinstance(value, str)}

        results = [summarize_metadata(result) for result in results]

    # Set in design object
    design.results = results


def map_fixed_effects_aggregate(result: ResultDict, exist_ok: bool = False) -> ResultDict:
    key = b32_digest(result)[:8]

    model_directory = Path.cwd() / f"model-{key}"
    model_directory.mkdir(exist_ok=exist_ok, parents=True)

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
        mask_file_path = merge_mask(mask_files)

        # Ensure consistent naming
        mask_file = Path.cwd() / "mask.nii.gz"
        mask_file_path.rename(mask_file)

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
    tstat = flameo.outputs.tstats
    tdof = flameo.outputs.tdof
    zstat = flameo.outputs.zstats

    images = dict(
        effect=Path(cope_file),
        variance=Path(var_cope_file),
        t=Path(tstat),
        dof=Path(tdof),
        z=Path(zstat),
        mask=Path(mask_file),
    )

    # Remove unused files
    output_paths = set(images.values())
    for input_path in flameo.inputs.values():
        if not isinstance(input_path, (str, Path)):
            continue
        input_path = Path(input_path)
        if not input_path.is_file():
            continue
        if input_path in output_paths:
            continue
        logger.debug(f'Removing unused file "{input_path}"')
        input_path.unlink()

    result["images"] = images

    return result
