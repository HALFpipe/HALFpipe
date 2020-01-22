# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    File
)

import numpy as np
import pandas as pd


def _motion_cutoff(mean_fd_cutoff, fd_greater_0_5_cutoff, confounds=None):
    df_confounds = pd.read_csv(confounds, sep="\t")

    # motion_report part
    mean_fd = df_confounds["FramewiseDisplacement"].mean()

    fd_greater_0_5 = np.mean(df_confounds["FramewiseDisplacement"] > 0.5)

    return not (mean_fd > mean_fd_cutoff or
                fd_greater_0_5 > fd_greater_0_5_cutoff)


class MotionCutoffInputSpec(TraitedSpec):
    confounds = File(exists=True, desc="input confounds file")

    mean_fd_cutoff = traits.Float(mandatory=True)
    fd_greater_0_5_cutoff = traits.Float(mandatory=True)


class MotionCutoffOutputSpec(TraitedSpec):
    keep = traits.Bool(desc="Decision, true means keep")


class MotionCutoff(SimpleInterface):
    """
    Tests if framewise displacement is greater than the specified cutoffs
    """

    input_spec = MotionCutoffInputSpec
    output_spec = MotionCutoffOutputSpec

    def _run_interface(self, runtime):
        keep = _motion_cutoff(
            confounds=self.inputs.confounds,
        )
        self._results["keep"] = keep

        return runtime
