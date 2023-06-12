# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import File, SimpleInterface, TraitedSpec, isdefined, traits
from nipype.interfaces.base.support import Bunch

from ...utils.path import split_ext


class SplitByFileTypeInputSpec(TraitedSpec):
    files = traits.List(File(exists=True))


class SplitByFileTypeOutputSpec(TraitedSpec):
    tsv_files = traits.List(File(exists=True))
    nifti_files = traits.List(File(exists=True))


class SplitByFileType(SimpleInterface):
    input_spec = SplitByFileTypeInputSpec
    output_spec = SplitByFileTypeOutputSpec

    def _run_interface(self, runtime: Bunch) -> Bunch:
        files = self.inputs.files

        tsv_files: list[str] = list()
        nifti_files: list[str] = list()

        if isdefined(files):
            for file in files:
                _, ext = split_ext(file)

                if ext in [".tsv"]:
                    tsv_files.append(file)

                elif ext in [".nii", ".nii.gz"]:
                    nifti_files.append(file)

        self._results["tsv_files"] = tsv_files
        self._results["nifti_files"] = nifti_files

        return runtime
