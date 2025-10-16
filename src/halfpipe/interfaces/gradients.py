# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

import nibabel as nib
import numpy as np
import pandas as pd
from nipype.interfaces.base import (
    BaseInterface,
    BaseInterfaceInputSpec,
    File,
    TraitedSpec,
    traits,
)
from nipype.interaces.base.traits.api import Union
from nipype.interfaces.base.support import Bunch

savetxt_argdict = dict(fmt="%.10f", delimiter="\t")

##############
# DRAFT CODE #
##############
# This code is a draft to implement brainspace gradients in HALFpipe

class GradientsInputSpec(BaseInterfaceInputSpec):
    # https://brainspace.readthedocs.io/en/latest/generated/brainspace.gradient.gradient.GradientMaps.html#brainspace.gradient.gradient.GradientMaps
    # GradientMaps params
    n_components = traits.Int(default=10, 
        desc="Number of gradients. Default is 10.")
    approach = traits.Str(default='dm', 
        desc="Embedding approach. Default is ‘dm’. Possible options: {'dm','le','pca'} for diffusion maps, Laplacian eigenmaps, and PCA respectively.")
    # traits.Union will use None as default bc it is first
    kernel = traits.Union(None, Str(), 
        desc="Possible options: {‘pearson’, ‘spearman’, ‘cosine’, ‘normalized_angle’, ‘gaussian’}. If None, use input matrix. Default is None.")
    random_state = traits.Union(None, Int(), 
        desc="Random state. Default is None.")
    alignment = traits.Union(None, Str(), 
        desc="Alignment approach. Only used when two or more datasets are provided. If None, no alignment is performed. Default is None. "
        "If ‘procrustes’, datasets are aligned using generalized procrustes analysis. "
        "If ‘joint’, datasets are embedded simultaneously based on a joint affinity matrix built from the individual datasets. This option is only available for ‘dm’ and ‘le’ approaches.")

    # .fit params
    # TODO


class ConnectivityMeasureOutputSpec(TraitedSpec):
    # Outputs from gradient computation:
    # - gradients
    # ...
    # TODO
    somefeat = None


class Gradients(BaseInterface):
    """
    Nipype interfaces to calculate gradients using brainspace.
    """

    input_spec = GradientsInputSpec
    output_spec = GradientsOutputSpec

    def _run_interface(self, runtime: Bunch) -> Bunch:
        # See connectivity.py for format
        return None

    def _list_outputs(self):
        # See connectivity.py for format
        return None