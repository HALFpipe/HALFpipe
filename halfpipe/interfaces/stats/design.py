# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import numpy as np
import pandas as pd
from nipype.interfaces.base import File, SimpleInterface, TraitedSpec, traits

from ...ingest.design import parse_design
from ...stats.design import group_design, intercept_only_design


class GroupDesignInputSpec(TraitedSpec):
    spreadsheet = File(exist=True, mandatory=True)
    contrastdicts = traits.List(
        traits.Dict(traits.Str, traits.Any),
        mandatory=True,
    )
    variabledicts = traits.List(
        traits.Dict(traits.Str, traits.Any),
        mandatory=True,
    )
    subjects = traits.List(traits.Str, mandatory=True)


class DesignOutputSpec(TraitedSpec):
    regressors = traits.Dict(traits.Str, traits.Any)
    contrasts = traits.List()
    contrast_numbers = traits.List(traits.Str())
    contrast_names = traits.List(traits.Str())


class GroupDesign(SimpleInterface):
    """interface to construct a group design"""

    input_spec = GroupDesignInputSpec
    output_spec = DesignOutputSpec

    def _run_interface(self, runtime):
        regressors, contrasts, numbers, names = group_design(
            spreadsheet=self.inputs.spreadsheet,
            contrastdicts=self.inputs.contrastdicts,
            variabledicts=self.inputs.variabledicts,
            subjects=self.inputs.subjects,
        )
        self._results["regressors"] = regressors
        self._results["contrasts"] = contrasts
        self._results["contrast_numbers"] = numbers
        self._results["contrast_names"] = names

        return runtime


class InterceptOnlyDesignInputSpec(TraitedSpec):
    n_copes = traits.Range(low=1, desc="number of inputs")


class InterceptOnlyDesign(SimpleInterface):
    """interface to construct a group design"""

    input_spec = InterceptOnlyDesignInputSpec
    output_spec = DesignOutputSpec

    def _run_interface(self, runtime):
        regressors, contrasts, numbers, names = intercept_only_design(
            self.inputs.n_copes
        )
        self._results["regressors"] = regressors
        self._results["contrasts"] = contrasts
        self._results["contrast_numbers"] = numbers
        self._results["contrast_names"] = names

        return runtime


class DesignSpec(TraitedSpec):
    regressors = traits.Dict(
        traits.Str,
        traits.List(traits.Float),
        mandatory=True,
    )
    contrasts = traits.List(
        traits.Either(
            traits.Tuple(
                traits.Str,
                traits.Enum("T"),
                traits.List(traits.Str),
                traits.List(traits.Float),
            ),
            traits.Tuple(
                traits.Str,
                traits.Enum("F"),
                traits.List(
                    traits.Tuple(
                        traits.Str,
                        traits.Enum("T"),
                        traits.List(traits.Str),
                        traits.List(traits.Float),
                    ),
                ),
            ),
        ),
        mandatory=True,
    )


class MakeDesignTsvInputSpec(DesignSpec):
    row_index = traits.Any(mandatory=True)


class MakeDesignTsvOutputSpec(TraitedSpec):
    design_tsv = File(exists=True)
    contrasts_tsv = File(exists=True)


class MakeDesignTsv(SimpleInterface):
    input_spec = MakeDesignTsvInputSpec
    output_spec = MakeDesignTsvOutputSpec

    def _run_interface(self, runtime):
        design_matrix, contrast_matrices = parse_design(
            self.inputs.regressors, self.inputs.contrasts
        )

        design_matrix.index = self.inputs.row_index

        self._results["design_tsv"] = Path.cwd() / "design.tsv"
        design_matrix.to_csv(
            self._results["design_tsv"], sep="\t", index=True, na_rep="n/a", header=True
        )

        index: list[str] = list()
        for contrast_name, contrast_matrix in contrast_matrices.items():
            for _ in range(contrast_matrix.shape[0]):
                index.append(contrast_name)

        contrast_data_frame = pd.DataFrame(
            np.concatenate(list(contrast_matrices.values()), axis=0),
            index=index,
            columns=design_matrix.columns,
        )

        self._results["contrasts_tsv"] = Path.cwd() / "contrasts.tsv"
        contrast_data_frame.to_csv(
            self._results["contrasts_tsv"],
            sep="\t",
            index=True,
            na_rep="n/a",
            header=True,
        )

        return runtime
