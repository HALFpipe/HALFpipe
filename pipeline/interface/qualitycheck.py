# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import json

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    Directory
)


def _qualitycheck(base_directory=None, subject=None, task=None):
    qcresult_fname = os.path.join(base_directory,
                                  "qualitycheck",
                                  "qcresult.json")

    qcresult = {}
    if os.path.isfile(qcresult_fname):
        with open(qcresult_fname) as qcresult_file:
            qcresult = json.load(qcresult_file)

    is_good = True
    for s, value0 in qcresult.items():
        if s == subject:
            for t, value1 in value0.items():
                for run, value2 in value1.items():
                    if t == "T1w" or t == task:
                        for k, v in value2.items():
                            if v == "bad":
                                is_good = False

    return is_good


class QualityCheckInputSpec(TraitedSpec):
    base_directory = Directory(desc="base directory")
    subject = traits.Str(desc="subject name")
    task = traits.Str(desc="task name")


class QualityCheckOutputSpec(TraitedSpec):
    keep = traits.Bool(desc="Decision, true means keep")


class QualityCheck(SimpleInterface):
    """

    """

    input_spec = QualityCheckInputSpec
    output_spec = QualityCheckOutputSpec

    def _run_interface(self, runtime):
        keep = _qualitycheck(
            base_directory=self.inputs.base_directory,
            subject=self.inputs.subject,
            task=self.inputs.task,
        )
        self._results["keep"] = keep

        return runtime
