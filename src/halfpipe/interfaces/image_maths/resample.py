# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import nibabel as nib
import numpy as np
from nipype.interfaces.base import File, InputMultiObject, isdefined, traits
from templateflow.api import get as get_template

from ...resource import get as getresource
from ...utils.image import nvol
from ..fixes.applytransforms import ApplyTransforms, ApplyTransformsInputSpec


class ResampleInputSpec(ApplyTransformsInputSpec):
    """
    Input specification for the Resample interface. It inherits the input_image
    trait from ApplyTransformsInputSpec and includes additional fields
    specific to the resampling process.

    Parameters
    ----------
    input_space : str, optional
        The space of the input image
    reference_space : str
        The space of the reference image
    reference_res : int, optional
        The resolution of the reference image. Typically 1, 2, or 3.
    lazy : bool
        If True, resampling is performed only if necessary. By default True.
    reference_image : path-like, optional
        The path to the reference image to which the input image will be warped
    transforms : list of path-like or 'identity', optional
        A list of transform files or the string 'identity'. The transforms
        are applied in reverse order. This is not a mandatory field.
    """

    input_space = traits.Either(
        "MNI152NLin6Asym", "MNI152NLin2009cAsym", mandatory=False
    )
    reference_space = traits.Either(
        "MNI152NLin6Asym", "MNI152NLin2009cAsym", mandatory=True
    )
    reference_res = traits.Int(mandatory=False)
    lazy = traits.Bool(default=True, usedefault=True, desc="only resample if necessary")

    # make not mandatory as these inputs will be computed from other inputs
    reference_image = File(
        argstr="--reference-image %s",
        mandatory=False,
        desc="reference image space that you wish to warp INTO",
        exists=True,
    )
    transforms = InputMultiObject(
        traits.Either(File(exists=True), "identity"),
        argstr="%s",
        mandatory=False,
        desc="transform files: will be applied in reverse order. For "
        "example, the last specified transform will be applied first.",
    )


class Resample(ApplyTransforms):
    """
    This class extends a Nipype interface for resampling neuroimaging data. It
    inherits from ApplyTransforms and uses the ResampleInputSpec for inputs.

    Methods
    -------
    _run_interface(runtime, correct_return_codes=(0,))
        Calls the resampling operation. Determines if resampling is
        necessary based on input and reference image properties, applies
        transformations, and handles the resampling process.
    _list_outputs()
        Returns the output file paths after resampling is complete. If
        resampling is not performed, it returns the input image path.
    """

    input_spec = ResampleInputSpec

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        """
        This method executes the resampling operation by calling the parent
        class ApplyTransforms, which wraps an ANTS command line call.

        Returns
        ----------
        runtime : object
            The runtime object from the Nipype interface.
        """

        self.resample = False

        reference_space = self.inputs.reference_space
        reference_res = (
            self.inputs.reference_res if isdefined(self.inputs.reference_res) else None
        )

        if not isdefined(self.inputs.reference_image):
            if reference_res is not None:
                self.inputs.reference_image = get_template(
                    reference_space,
                    resolution=reference_res,
                    desc="brain",
                    suffix="mask",
                )

        if not isdefined(self.inputs.dimension):
            self.inputs.dimension = 3

        input_matches_reference = False
        # Check if input image shape and affine matches reference image.
        if isdefined(self.inputs.input_image):
            input_image = nib.nifti1.load(self.inputs.input_image)
            reference_image = nib.nifti1.load(self.inputs.reference_image)
            input_matches_reference = input_image.shape[:3] == reference_image.shape[:3]
            input_matches_reference = input_matches_reference and np.allclose(
                input_image.affine,
                reference_image.affine,
                atol=1e-2,
                rtol=1e-2,  # Use a tolerance of 0.01 mm
            )
            input_image_nvol = nvol(input_image)
            if input_image_nvol > 0:
                self.inputs.input_image_type = 3  # Set to time series

        if not isdefined(self.inputs.transforms):
            transforms = ["identity"]

            input_space = self.inputs.input_space
            if isdefined(input_space):
                if input_space != reference_space:
                    xfm = getresource(
                        f"tpl_{reference_space}_from_{input_space}_mode_image_xfm.h5"
                    )
                    assert Path(xfm).is_file()
                    transforms = [str(xfm)]

            self.inputs.transforms = transforms
        else:
            transforms = ["custom"]

        # Only resample if necessary
        if (
            not input_matches_reference
            or set(transforms) != set(["identity"])
            or not self.inputs.lazy
        ):
            self.resample = True
            runtime = super(
                Resample, self
            )._run_interface(  # Use super class ApplyTransforms to apply transforms
                runtime, correct_return_codes
            )

        return runtime

    def _list_outputs(self):
        if self.resample:
            return super(Resample, self)._list_outputs()
        else:
            outputs = self.output_spec().get()
            outputs["output_image"] = self.inputs.input_image
            return outputs
