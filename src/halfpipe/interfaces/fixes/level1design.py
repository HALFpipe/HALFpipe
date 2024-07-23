# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.fsl.model as fslm
from nipype.interfaces.base import traits


class Level1DesignInputSpec(fslm.Level1DesignInputSpec):
    bases = traits.Either(
        traits.Dict(traits.Enum("dgamma"), traits.Dict(traits.Enum("derivs"), traits.Bool)),
        traits.Dict(
            traits.Enum("gamma"),
            traits.Dict(traits.Enum("derivs", "gammasigma", "gammadelay")),
        ),
        traits.Dict(
            traits.Enum("custom"),
            traits.Dict(traits.Enum("bfcustompath", "basisfnum"), traits.Any),
        ),
        traits.Dict(traits.Enum("none"), traits.Dict()),
        traits.Dict(traits.Enum("none"), traits.Enum(None)),
        mandatory=True,
        desc=("name of basis function and options e.g., " "{'dgamma': {'derivs': True}}"),
    )


class Level1Design(fslm.Level1Design):
    input_spec = Level1DesignInputSpec
