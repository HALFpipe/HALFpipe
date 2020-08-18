# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from inspect import getmembers, isfunction, signature

from nipype.interfaces.base import (
    DynamicTraitedSpec,
    isdefined
)
from nipype.interfaces.io import add_traits, IOBase

import halfpipe.utils as halfpipeutils


def predicate(fn):
    if isfunction(fn):
        if len(signature(fn).parameters) == 1:
            return True
    return False


utilfunctions = dict(getmembers(halfpipeutils, predicate))


class Exec(IOBase):
    input_spec = DynamicTraitedSpec
    output_spec = DynamicTraitedSpec

    def __init__(self, fieldtpls=[], **inputs):
        super(Exec, self).__init__(**inputs)

        self.fieldtpls = fieldtpls

        for fieldname, ufn in self.fieldtpls:
            if ufn is not None and ufn not in utilfunctions:
                raise ValueError(f'Unknown function name "{ufn}" for field "{fieldname}"')

        fieldnames, _ = zip(*self.fieldtpls)
        add_traits(self.inputs, [*fieldnames])

    def _add_output_traits(self, base):
        fieldnames, _ = zip(*self.fieldtpls)
        return add_traits(base, [*fieldnames])

    def _list_outputs(self):
        outputs = self._outputs().get()

        for fieldname, ufn in self.fieldtpls:
            input = getattr(self.inputs, fieldname)
            if isdefined(input):
                if ufn is not None:
                    input = utilfunctions[ufn](input)
                outputs[fieldname] = input

        return outputs
