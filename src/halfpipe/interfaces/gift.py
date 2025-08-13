import os

import nibabel as nib
import numpy as np
import scipy
from nipype.interfaces.base import CommandLine, CommandLineInputSpec, File, TraitedSpec, traits

from .connectivity import savetxt_argdict


class GicaCmdInputSpec(CommandLineInputSpec):
    modality = traits.Enum("fmri", argstr="--modality %s", default="fmri")
    data = File(exists=True, mandatory=True, argstr="--data %s")
    mask = File(exists=True, mandatory=True, argstr="--mask %s")
    algorithm = traits.Enum("moo-icar", argstr="--algorithm %s", default="moo-icar")
    templates = File(exists=True, mandatory=True, argstr="--templates %s")
    performance = traits.Enum(1, 2, 3, argstr="--performance %d", default=1)


class GicaCmdOutputSpec(TraitedSpec):
    components = File(exists=True)
    timecourses = File(exists=True)
    mask = File(exists=True)
    fnc_corrs = File(exists=True)


class GicaCmd(CommandLine):
    input_spec = GicaCmdInputSpec
    output_spec = GicaCmdOutputSpec
    _cmd = "gica_cmd"

    def _list_outputs(self):
        outputs = self.output_spec().get()

        outputs["components"] = os.path.abspath("gica_cmd_sub01_component_ica_s1_.nii")
        outputs["mask"] = os.path.abspath("gica_cmdMask.nii")

        timecourses_image = nib.nifti1.load("gica_cmd_sub01_timecourses_ica_s1_.nii")
        timecourses = timecourses_image.get_fdata()
        timecourses = timecourses.squeeze()
        np.savetxt("timecourses.tsv", timecourses, **savetxt_argdict)
        outputs["timecourses"] = os.path.abspath("timecourses.tsv")

        postprocessing_results = scipy.io.matlab.loadmat("gica_cmd_postprocess_results/gica_cmd_post_process_sub_001.mat")
        fnc_corrs = postprocessing_results["fnc_corrs"].squeeze(0)
        np.savetxt("fnc_corrs.tsv", fnc_corrs, **savetxt_argdict)
        outputs["fnc_corrs"] = os.path.abspath("fnc_corrs.tsv")

        return outputs
