# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op
import json

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    Directory
)


def _qualitycheck(base_directory=None, subject=None, scan=None, run=None):
    qcresult_fname = op.join(base_directory,
                             "qualitycheck",
                             "qcresult.json")

    qcresult = {}
    if op.isfile(qcresult_fname):
        with open(qcresult_fname) as qcresult_file:
            qcresult = json.load(qcresult_file)

    is_good = True
    for s, value0 in qcresult.items():
        if s == subject:
            for t, value1 in value0.items():
                if scan is None or (t == "T1w" or t == scan):
                    for r, value2 in value1.items():
                        if run is None or run == r:
                            for k, v in value2.items():
                                if v == "bad":
                                    is_good = False

    return is_good


class QualityCheckInputSpec(TraitedSpec):
    base_directory = Directory(desc="base directory")
    subject = traits.Str(desc="subject name")
    scan = traits.Str(desc="scan name")
    run = traits.Str(desc="run name")


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
            scan=self.inputs.scan,
            run=self.inputs.run
        )
        self._results["keep"] = keep

        return runtime
