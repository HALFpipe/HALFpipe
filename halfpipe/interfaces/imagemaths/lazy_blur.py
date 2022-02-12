# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from math import isclose

from nipype.interfaces import afni


class LazyBlurToFWHM(afni.BlurToFWHM):
    @property
    def _should_run(self):
        return not isclose(self.inputs.fwhm, 0, abs_tol=1e-2) and self.inputs.fwhm > 0

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        if self._should_run:
            return super(LazyBlurToFWHM, self)._run_interface(
                runtime, correct_return_codes
            )

        runtime.stdout = ""
        runtime.stderr = ""
        runtime.merged = ""

        runtime.cmdline = ""
        runtime.returncode = 0
        runtime.success_codes = correct_return_codes

        return runtime

    def _list_outputs(self):
        if self._should_run:
            return super(LazyBlurToFWHM, self)._list_outputs()

        outputs = self._outputs()
        assert outputs is not None
        outputs = outputs.get()
        outputs["out_file"] = self.inputs.in_file

        return outputs
