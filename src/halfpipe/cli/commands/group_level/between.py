# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from argparse import Namespace
from copy import deepcopy
from dataclasses import dataclass, field
from itertools import starmap
from pathlib import Path
from typing import Any, Literal, Sequence

import pandas as pd

from .... import __version__
from ....design import Design, group_design, intercept_only_design, make_design_tsv
from ....logging import logger
from ....result.aggregate import summarize_metadata
from ....result.base import ResultDict
from ....result.bids.base import make_bids_prefix
from ....result.bids.images import save_images
from ....stats.algorithms import modelfit_aliases
from ....stats.fit import fit
from ....utils.data_frame import combine_first
from ....utils.format import format_tags
from .base import aliases
from .design import DesignBase
from .export import Atlas, DiscreteAtlas, ProbabilisticAtlas, export


@dataclass
class BetweenBase:
    arguments: Namespace

    output_directory: Path

    phenotype_frames: list[pd.DataFrame] = field(default_factory=list)
    covariate_frames: list[pd.DataFrame] = field(default_factory=list)
    atlas_coverage_frames: list[pd.DataFrame] = field(default_factory=list)

    prefix: str = field(init=False)

    def apply(
        self,
        result: ResultDict,
        design_base: DesignBase,
    ) -> None:
        # Get information about what we are running
        tags = result["tags"]
        subjects = tags.pop("sub")
        for key in ["contrast", "model"]:
            # Remove lower level tags
            if key in tags:
                del tags[key]
        logger.log(
            25,
            f"Processing tags {format_tags(tags)} for {len(subjects)} subjects",
        )

        # Remove variables for exporting from the data frame that holds the covariates
        self.apply_export_variables(design_base)

        # Rename the images to what the fit method expects
        images: dict[str, list[Path]] = result["images"]
        result["images"] = dict()
        for from_key, to_key in aliases.items():
            if from_key in images:
                images[to_key] = images.pop(from_key)
        # Extract the relevant keys from the image dictionary
        cope_paths = images["effect"]
        var_cope_paths = images.get("variance")
        mask_paths = images["mask"]
        # Create a design tuple
        if design_base.data_frame is not None:
            design = group_design(
                design_base.data_frame,
                design_base.contrasts,
                subjects,
            )
        else:
            design = intercept_only_design(len(subjects))

        self.apply_export(
            subjects,
            images,
            design,
            result,
        )
        self.apply_fit(
            subjects,
            cope_paths,
            var_cope_paths,
            mask_paths,
            design,
            result,
            design_base.model_name,
        )

    def apply_export_variables(self, design_base: DesignBase) -> None:
        export_variables: list[str] | None = self.arguments.export_variable
        if export_variables is None:
            return
        for name in export_variables:
            if name not in design_base.variable_sets:
                continue
            export_variables.extend(design_base.variable_sets[name])
        variable_dict = {name: design_base.drop_variable(name) for name in export_variables}
        variable_dict = {name: value for name, value in variable_dict.items() if value is not None}
        data_frame = pd.DataFrame(variable_dict)
        self.phenotype_frames.append(data_frame)

    def apply_fit(
        self,
        subjects: list[str],
        cope_paths: list[Path],
        var_cope_paths: list[Path] | None,
        mask_paths: list[Path],
        design: Design,
        result: ResultDict,
        model_name: str | None = None,
    ):
        (regressor_list, contrast_list, _, contrast_names) = design

        design_tsv, contrast_tsv = make_design_tsv(
            regressor_list,
            contrast_list,
            subjects,
        )
        outputs: dict[str, str | Sequence[Literal[False] | str]] = dict(
            design_matrix=str(design_tsv),
            contrast_matrix=str(contrast_tsv),
        )
        outputs.update(
            fit(
                cope_paths,
                var_cope_paths,
                mask_paths,
                regressor_list,
                contrast_list,
                self.arguments.algorithm,
                self.arguments.nipype_n_procs,
            )
        )
        # Apply rules from model fit aliases
        for from_key, to_key in modelfit_aliases.items():
            if from_key in outputs:
                outputs[to_key] = outputs.pop(from_key)

        results: list[ResultDict] = list()

        # Top-level result
        images: dict[str, str] = {key: value for key, value in outputs.items() if isinstance(value, str)}
        result = summarize_metadata(result)
        if model_name is not None:
            result["tags"]["model"] = model_name
        result["images"] = images

        sources: list[str] = list()
        sources.extend(str(cope_path) for cope_path in cope_paths)
        if var_cope_paths is not None:
            sources.extend(str(var_cope_path) for var_cope_path in var_cope_paths)
        sources.extend(str(mask_path) for mask_path in mask_paths)
        result["metadata"]["sources"] = sources
        result["metadata"]["halfpipe_version"] = __version__

        results.append(result)

        # Per-contrast results
        for i, contrast_name in enumerate(contrast_names):
            contrast_images = {
                key: value[i] for key, value in outputs.items() if isinstance(value, list) and isinstance(value[i], str)
            }
            if len(contrast_images) == 0:
                continue
            result = deepcopy(result)
            result["tags"]["contrast"] = contrast_name
            if model_name is not None:
                result["tags"]["model"] = model_name
            result["images"] = contrast_images
            results.append(result)

        save_images(results, self.output_directory)

    def apply_export(
        self,
        subjects: list[str],
        images: dict[str, Any],
        design: Design,
        result: ResultDict,
    ) -> None:
        prefix = make_bids_prefix(result["tags"])

        atlases: list[Atlas] = list()
        if self.arguments.export_atlas is not None:
            atlases.extend(starmap(DiscreteAtlas.from_args, self.arguments.export_atlas))
        if self.arguments.export_modes is not None:
            atlases.extend(starmap(ProbabilisticAtlas.from_args, self.arguments.export_modes))

        logger.info(f"Exporting atlases {atlases}")
        if len(atlases) == 0:
            return

        regressor_list, contrast_list, _, _ = design
        phenotype_frame, covariate_frame, atlas_coverage_frame = export(
            prefix,
            subjects,
            images,
            regressor_list,
            contrast_list,
            atlases,
            self.arguments.nipype_n_procs,
        )

        self.phenotype_frames.append(phenotype_frame)
        self.covariate_frames.append(covariate_frame)
        self.atlas_coverage_frames.append(atlas_coverage_frame)

    def write_outputs(self) -> None:
        csv_kwargs: dict[str, Any] = dict(sep="\t", index=True, na_rep="n/a")

        if len(self.phenotype_frames) > 0:
            phenotype_frame = combine_first(self.phenotype_frames)
            # Sort columns to alphabetical order.
            phenotype_frame.sort_index(axis=1, inplace=True)
            phenotype_path = self.output_directory / "phenotypes.tsv"
            phenotype_frame.to_csv(phenotype_path, **csv_kwargs)
        else:
            logger.warning("No phenotypes were exported")

        if len(self.covariate_frames) > 0:
            covariate_frame = combine_first(self.covariate_frames)
            covariate_path = self.output_directory / "covariates.tsv"
            covariate_frame.to_csv(covariate_path, **csv_kwargs)
        else:
            logger.warning("No covariates were exported")

        if len(self.atlas_coverage_frames) > 0:
            atlas_coverage_frame = combine_first(self.atlas_coverage_frames)
            # Sort columns to alphabetical order.
            atlas_coverage_frame.sort_index(axis=1, inplace=True)
            coverage_path = self.output_directory / "atlas_coverages.tsv"
            atlas_coverage_frame.to_csv(coverage_path, **csv_kwargs)
        else:
            logger.warning("No atlas coverages were exported")
