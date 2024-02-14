# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import ants, fsl

from ...interfaces.image_maths.resample import Resample
from ..constants import Constants
from ..memory import MemoryCalculator


def init_jacobian_wf(
    transform: Path | None = None,
    memcalc: MemoryCalculator | None = None,
) -> pe.Workflow:
    """
    Workflow for calculating a jacobian determinant from a transform.
    Each voxel in the resulting image is the size in mm^3 of the voxel in subject space.
    See also https://github.com/cookpa/antsJacobianExample

    Parameters
    ----------
    transform : Path, optional
        The path to the transform file to use. If not specified, the transform will be taken from the `inputnode`.
    memcalc : MemoryCalculator, optional
        The memory calculator to use for estimating memory usage. Defaults to the default memory calculator.

    Returns
    -------
    workflow : Workflow
        The initialized workflow for calculating the jacobian determinant.
    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    workflow = pe.Workflow(name="jacobian_wf")

    # Input and output
    inputnode = pe.Node(
        niu.IdentityInterface(fields=["transform"]),
        name="inputnode",
    )
    if transform is not None:
        inputnode.inputs.transform = str(transform)

    outputnode = pe.Node(niu.IdentityInterface(fields=["jacobian"]), name="outputnode")

    # Create composite transform
    create_composite_transform = pe.Node(
        Resample(
            dimension=3,
            output_image="composite_transform.nii.gz",
            interpolation="LanczosWindowedSinc",
            print_out_composite_warp_file=True,
            reference_space=Constants.reference_space,
            reference_res=Constants.reference_res,
        ),
        name="create_composite_transform",
        mem_gb=memcalc.volume_gb * 10,  # TODO measure this
    )
    workflow.connect(inputnode, "transform", create_composite_transform, "transforms")

    # Calculate jacobian
    create_jacobian = pe.Node(
        ants.CreateJacobianDeterminantImage(
            imageDimension=3,
            outputImage="jacobian.nii.gz",
            doLogJacobian=0,
            # Use geometric method, which is  based on calculating the area of a
            # transformed triangle and comparing it to the original area
            # The ratio is the value for each voxel. We choose this method instead
            # of the finite difference method because the calculation is conceptually
            # closer to what we want to measure./
            # In practice, both methods yield identical results. See also
            # https://sourceforge.net/p/advants/discussion/840260/thread/84d24a38/#7a8e/2206
            useGeometric=1,
        ),
        name="create_jacobian",
        mem_gb=memcalc.volume_gb * 10,  # TODO measure this
    )
    workflow.connect(create_composite_transform, "output_image", create_jacobian, "deformationField")

    voxel_volume = Constants.reference_res**3
    scale_jacobian = pe.Node(
        fsl.ImageMaths(
            op_string=f"-mul {voxel_volume}",
            suffix="_scaled",
        ),
        name="scale_jacobian",
        mem_gb=memcalc.volume_gb,
    )
    workflow.connect(create_jacobian, "jacobian_image", scale_jacobian, "in_file")

    workflow.connect(scale_jacobian, "out_file", outputnode, "jacobian")

    return workflow
