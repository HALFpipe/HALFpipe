# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

import numpy as np
from brainspace.gradient.gradient import GradientMaps
from nipype.interfaces.base import (
    SimpleInterface,
    TraitedSpec,
    isdefined,
    traits,
)
from nipype.interfaces.base.support import Bunch

##############
# DRAFT CODE #
##############
# This code is a draft to implement brainspace gradients in HALFpipe
# TODO integrate file format load w/ HALFpipe
# TODO write corresponding workflow


class GradientsInputSpec(TraitedSpec):
    """Inputs for gradients, see https://brainspace.readthedocs.io/en/latest/generated/brainspace.gradient.gradient.GradientMaps.html#brainspace.gradient.gradient.GradientMaps"""

    # GradientMaps params
    # TODO cut these down/consider necessary
    n_components = traits.Int(
        default_value=10,
        usedefault=True,
        desc="Number of gradients. Default is 10.",
    )
    approach = traits.Str(
        default_value="dm",
        usedefault=True,
        desc="Embedding approach. Default is 'dm'. Possible options: {'dm','le','pca'} for diffusion maps, "
        "Laplacian eigenmaps, and PCA respectively.",
    )
    kernel = traits.Str(
        desc="Possible options: {'pearson', 'spearman', 'cosine', 'normalized_angle', 'gaussian'}. If None, use input matrix. "
        "Default is None.",
    )
    random_state = traits.Int(desc="Random state. Default is None.")
    alignment = traits.Str(
        default_value="procrustes",
        usedefault=True,
        desc="Alignment approach. Only used when two or more datasets are provided. If None, no alignment is performed. "
        "Default is None. If 'procrustes', datasets are aligned using generalized procrustes analysis. "
        "If 'joint', datasets are embedded simultaneously based on a joint affinity matrix built from the individual "
        "datasets. This option is only available for 'dm' and 'le' approaches.",
    )

    # .fit params
    correlation_matrix = traits.File(
        exists=True,
        mandatory=True,
        desc="Input matrix or list of matrices, shape = (n_samples, n_feat).",
    )
    gamma = traits.Float(
        desc="Inverse kernel width. Only used if kernel == 'gaussian'. If None, gamma=1/n_feat . Default is None.",
    )
    sparsity = traits.Float(
        desc="Proportion of the smallest elements to zero-out for each row. Default is 0.9.",
    )
    n_iter = traits.Int(
        default_value=10,
        usedefault=True,
        desc="Number of iterations for procrustes alignment. Default is 10.",
    )
    reference = traits.Array(
        desc="Initial reference for procrustes alignments, shape = (n_samples, n_feat). "
        "Only used when alignment == 'procrustes'. Default is None.",
    )  # update desc


class GradientsOutputSpec(TraitedSpec):
    # Outputs from gradient computation:
    lambdas = traits.File(
        desc="Eigenvalues for each dataset, shape = (n_components,).",
    )
    gradients = traits.File(
        desc="Gradients (i.e., eigenvectors), shape = (n_samples, n_components).",
    )
    aligned = traits.File(
        desc="Aligned gradients, shape = (n_samples, n_components). None if alignment is None or only one dataset is used.",
    )


class Gradients(SimpleInterface):
    """Nipype interface to calculate gradients using brainspace."""

    input_spec = GradientsInputSpec
    output_spec = GradientsOutputSpec

    def _run_interface(self, runtime: Bunch) -> Bunch:
        correlation_matrix = np.loadtxt(self.inputs.correlation_matrix)

        alignment = self.inputs.alignment if isdefined(self.inputs.alignment) else None

        if alignment == "procrustes" and not isdefined(self.inputs.reference):
            raise ValueError("Reference must be provided for procrustes alignment.")

        gm = GradientMaps(
            n_components=self.inputs.n_components,
            approach=self.inputs.approach,
            kernel=self.inputs.kernel if isdefined(self.inputs.kernel) else None,
            random_state=self.inputs.random_state if isdefined(self.inputs.random_state) else None,
            alignment=alignment,
        ).fit(
            correlation_matrix,
            sparsity=self.inputs.sparsity if isdefined(self.inputs.sparsity) else None,
            gamma=self.inputs.gamma if isdefined(self.inputs.gamma) else None,
            n_iter=self.inputs.n_iter,
            reference=self.inputs.reference,
        )

        lambdas = gm.lambdas_
        gradients = gm.gradients_
        aligned = gm.aligned_

        savetxt_argdict = dict(fmt="%.10f", delimiter="\t")

        lambdas_file = op.abspath("lambdas.tsv")
        np.savetxt(lambdas_file, lambdas, **savetxt_argdict)

        gradients_file = op.abspath("gradients.tsv")
        np.savetxt(gradients_file, gradients, **savetxt_argdict)

        self._results["lambdas"] = lambdas_file
        self._results["gradients"] = gradients_file

        if aligned is not None:
            aligned_file = op.abspath("aligned.tsv")
            np.savetxt(aligned_file, aligned, **savetxt_argdict)
            self._results["aligned"] = aligned_file

        return runtime
