# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import pandas as pd
import numpy as np

from nipype.interfaces.base import TraitedSpec, SimpleInterface, traits, File

from ...io import parse_design
from ...utils import ravel


class DesignSpec(TraitedSpec):
    regressors = traits.Dict(
        traits.Str,
        traits.List(traits.Float),
        mandatory=True,
    )
    contrasts = traits.List(
        traits.Either(
            traits.Tuple(traits.Str, traits.Enum("T"), traits.List(traits.Str),
                         traits.List(traits.Float)),
            traits.Tuple(traits.Str, traits.Enum("F"),
                         traits.List(
                             traits.Tuple(traits.Str, traits.Enum("T"),
                                          traits.List(traits.Str),
                                          traits.List(traits.Float)),
            ))
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
        dmat, cmatdict = parse_design(self.inputs.regressors, self.inputs.contrasts)

        dmat.index = self.inputs.row_index

        self._results["design_tsv"] = Path.cwd() / "design.tsv"
        dmat.to_csv(
            self._results["design_tsv"], sep="\t", index=True, na_rep="n/a", header=True
        )

        cmat = pd.DataFrame(
            np.concatenate([*cmatdict.values()], axis=0),
            index=ravel([[k] * v.shape[0] for k, v in cmatdict.items()]),
            columns=dmat.columns
        )

        self._results["contrasts_tsv"] = Path.cwd() / "contrasts.tsv"
        cmat.to_csv(
            self._results["contrasts_tsv"], sep="\t", index=True, na_rep="n/a", header=True
        )

        return runtime
