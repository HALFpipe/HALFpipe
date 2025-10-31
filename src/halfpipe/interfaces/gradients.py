# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op


from nipype.interfaces.base import (
    BaseInterface,
    BaseInterfaceInputSpec,
#    File,
    TraitedSpec,
    traits,
)


from nipype.interfaces.base.support import Bunch

import numpy as np
from brainspace.gradient.gradient import GradientMaps

##############
# DRAFT CODE #
##############
# This code is a draft to implement brainspace gradients in HALFpipe
# TODO pass inputs as files to integrate w/ HALFpipe
# TODO write corresponding workflow

class GradientsInputSpec(BaseInterfaceInputSpec):
    """ Inputs for gradients, see https://brainspace.readthedocs.io/en/latest/generated/brainspace.gradient.gradient.GradientMaps.html#brainspace.gradient.gradient.GradientMaps """
    # GradientMaps params
    n_components = traits.Int(10, usedefault=True,
        desc="Number of gradients. Default is 10.")
    approach = traits.Str('dm', usedefault=True,
        desc="Embedding approach. Default is ‘dm’. Possible options: {'dm','le','pca'} for diffusion maps, Laplacian eigenmaps, and PCA respectively.")
    kernel = traits.Union(None, traits.Str, usedefault=True,
        desc="Possible options: {‘pearson’, ‘spearman’, ‘cosine’, ‘normalized_angle’, ‘gaussian’}. If None, use input matrix. Default is None.")
    random_state = traits.Union(None, traits.Int, usedefault=True,
        desc="Random state. Default is None.")
    alignment = traits.Union(None, traits.Str, usedefault=True,
        desc="Alignment approach. Only used when two or more datasets are provided. If None, no alignment is performed. Default is None. "
        "If ‘procrustes’, datasets are aligned using generalized procrustes analysis. "
        "If ‘joint’, datasets are embedded simultaneously based on a joint affinity matrix built from the individual datasets. This option is only available for ‘dm’ and ‘le’ approaches.")

    # .fit params
    x = traits.Union(traits.Array, traits.List(trait=traits.Array), usedefault=True,
        desc="Input matrix or list of matrices, shape = (n_samples, n_feat).")
    gamma = traits.Union(None, traits.Float, usedefault=True,
        desc="Inverse kernel width. Only used if kernel == 'gaussian'. If None, gamma=1/n_feat . Default is None.")
    sparsity = traits.Float(0.9, usedefault=True,
        desc="Proportion of the smallest elements to zero-out for each row. Default is 0.9.")
    n_iter = traits.Int(10, usedefault=True,
        desc="Number of iterations for procrustes alignment. Default is 10.")
    reference = traits.Union(None, traits.Array, usedefault=True,
        desc="Initial reference for procrustes alignments, shape = (n_samples, n_feat). Only used when alignment == 'procrustes'. Default is None.")
    # skipping kwargs


class GradientsOutputSpec(TraitedSpec):
    # Outputs from gradient computation:
    lambdas = traits.Union(traits.Array, traits.List(trait=traits.Array),
        desc="Eigenvalues for each datatset, shape = (n_components,).")
    gradients = traits.Union(traits.Array, traits.List(trait=traits.Array),
        desc="Gradients (i.e., eigenvectors), shape = (n_samples, n_components).")
    aligned = traits.Union(None, traits.List(trait=traits.Array),
        desc="Aligned gradients, shape = (n_samples, n_components). None if alignment is None or only one dataset is used.")
    


class Gradients(BaseInterface):
    """ Nipype interface to calculate gradients using brainspace. """
    input_spec = GradientsInputSpec
    output_spec = GradientsOutputSpec

    def _run_interface(self, runtime: Bunch) -> Bunch:

        gm = GradientMaps(
            n_components = self.inputs.n_components,
            approach = self.inputs.approach,
            kernel = self.inputs.kernel,
            random_state = self.inputs.random_state,
            alignment = self.inputs.alignment,
            )

        gm.fit(
            self.inputs.x,
            sparsity = self.inputs.sparsity,
            gamma = self.inputs.gamma,
            n_iter = self.inputs.n_iter,
            reference = self.inputs.reference
        )

        self._lambdas = gm.lambdas_ 
        self._gradients = gm.gradients_
        self._aligned = gm.aligned_

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()

        savetxt_argdict = dict(fmt="%.10f", delimiter="\t")
        
        lambdas_file = op.abspath("lambdas.tsv")
        np.savetxt(lambdas_file, self._lambdas, **savetxt_argdict)

        gradients_file = op.abspath("gradients.tsv")
        np.savetxt(gradients_file, self._gradients, **savetxt_argdict)

        outputs["lambdas"] = lambdas_file
        outputs["gradients"] = gradients_file

        if self._aligned is not None:
            aligned_file = op.abspath("aligned.tsv")
            np.savetxt(aligned_file, self._aligned, **savetxt_argdict)
            outputs["aligned"] = aligned_file

        return outputs