# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import traceback
import os
from os import path as op
import json
import sys

from nipype.pipeline import engine as pe


def save_traceback(t, v, b, odir=os.getcwd()):
    name = str(v.__class__.__name__)
    mod_name = str(v.__class__.__module__)
    info = traceback.format_exception(t, v, b)
    data = {
        "class": name,
        "module": mod_name,
        "message": f"{v}",
        "tb": info
    }

    path = op.join(odir, f"{name}.txt")
    with open(path, "w") as fp:
        json.dump(data, fp, indent=4)
    sys.stdout.write("TryNode caught exception. " +
                     f"Saved exception to \"{path}\"\n")


class TryNode(pe.Node):
    """
    Nipype is written very much for pre-defined workflows
    When we make dynamic, execution time adjustments such as
    excluding subjects, it may be that some nodes can't be run as planned, and
    that's ok. We can still run the rest of the workflow
    However, nipype does not have any way to support this flexibility and will
    fail on exceptions
    The TryNode solves this issue by simply ignoring any errors that may occur
    """
    def run(self, updatehash=False):
        try:
            super(TryNode, self).run(updatehash=updatehash)
        except Exception:
            save_traceback(*sys.exc_info(), odir=self.output_dir())

    def _get_inputs(self):
        try:
            super(TryNode, self)._get_inputs()
        except Exception:
            save_traceback(*sys.exc_info(), odir=self.output_dir())
        self._got_inputs = True


class TryMapNode(pe.MapNode):
    def run(self, updatehash=False):
        try:
            super(TryMapNode, self).run(updatehash=updatehash)
        except Exception:
            save_traceback(*sys.exc_info(), odir=self.output_dir())

    def _get_inputs(self):
        try:
            super(TryNode, self)._get_inputs()
        except Exception:
            save_traceback(*sys.exc_info(), odir=self.output_dir())
        self._got_inputs = True

    def _check_iterfield(self):
        try:
            super(TryNode, self)._check_iterfield()
        except Exception:
            save_traceback(*sys.exc_info(), odir=self.output_dir())
