import os

from nipype.interfaces.base import CommandLine, CommandLineInputSpec, File, TraitedSpec, traits


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


class GicaCmd(CommandLine):
    input_spec = GicaCmdInputSpec
    output_spec = GicaCmdOutputSpec
    _cmd = "gica_cmd"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["components"] = os.path.abspath("gica_cmd_sub01_component_ica_s1_.nii")
        outputs["timecourses"] = os.path.abspath("gica_cmd_sub01_timecourses_ica_s1_.nii")
        return outputs
