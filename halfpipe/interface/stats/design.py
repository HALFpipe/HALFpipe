# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import pandas as pd

from nipype.interfaces.base import TraitedSpec, SimpleInterface, traits, File

from ...io import parse_design


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
    row_index = traits.List(traits.Any, mandatory=True)


class MakeDesignTsvOutputSpec(TraitedSpec):
    design_tsv = File(exists=True)
    contrasts_tsv = File(exists=True)


class MakeDesignTsv(SimpleInterface):
    input_spec = MakeDesignTsvInputSpec
    output_spec = MakeDesignTsvOutputSpec

    def _run_interface(self, runtime):
        dmat, cmatdict = parse_design(self.inputs.regressors, self.inputs.contrasts)

