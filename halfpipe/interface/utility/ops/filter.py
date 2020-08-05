# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re

from nipype.interfaces.base import (
    isdefined,
    traits,
    DynamicTraitedSpec,
    BaseInterfaceInputSpec,
)
from nipype.interfaces.io import add_traits, IOBase


class Filter(IOBase):
    """Basic interface class to merge inputs into lists

    """

    input_spec = DynamicTraitedSpec
    output_spec = DynamicTraitedSpec

    def __init__(self, numinputs=0, fieldnames=["value"], **inputs):
        super(Filter, self).__init__(**inputs)
        self._numinputs = numinputs
        self._fieldnames = fieldnames
        if numinputs >= 1:
            for fieldname in self._fieldnames:
                input_names = ["{}{}".format(fieldname, (i + 1)) for i in range(numinputs)]
                add_traits(self.inputs, input_names)
            isenabled_input_names = ["is_enabled%d" % (i + 1) for i in range(numinputs)]
            add_traits(self.inputs, isenabled_input_names, trait_type=traits.Bool)
        else:
            input_names = []

    def _add_output_traits(self, base):
        return add_traits(base, self._fieldnames)

    def _list_outputs(self):
        outputs = self._outputs().get()

        if self._numinputs < 1:
            return outputs

        def getisenabled(idx):
            return getattr(self.inputs, "is_enabled%d" % (idx + 1))

        def getval(fieldname, idx):
            return getattr(self.inputs, "{}{}".format(fieldname, (idx + 1)))

        for fieldname in self._fieldnames:
            outputs[fieldname] = []

        for idx in range(self._numinputs):
            use = isdefined(getisenabled(idx)) and getisenabled(idx)
            for fieldname in self._fieldnames:  # all need to be defined
                use &= isdefined(getval(fieldname, idx))
            if use:
                for fieldname in self._fieldnames:
                    outputs[fieldname].append(getval(fieldname, idx))

        return outputs


class FilterListInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    keys = traits.List(traits.Str(), mandatory=True)
    pattern = traits.Str(mandatory=True)


class FilterList(IOBase):
    input_spec = FilterListInputSpec
    output_spec = DynamicTraitedSpec

    def __init__(self, fields=None, **inputs):  # filterdict=None,
        super(FilterList, self).__init__(**inputs)
        if fields is not None:
            add_traits(self.inputs, fields)
        else:
            fields = []
        self._fields = fields

    def _add_output_traits(self, base):
        return add_traits(base, self._fields)

    def _list_outputs(self):
        outputs = self.output_spec().get()

        includelist = [
            re.match(self.inputs.pattern, in_value) is None for in_value in self.inputs.keys
        ]

        for field in self._fields:
            valuelist = getattr(self.inputs, field)
            if not isdefined(valuelist):
                continue
            if not isinstance(valuelist, list):
                valuelist = [valuelist]
            outputs[field] = [
                value for include, value in zip(includelist, valuelist) if include
            ]

        return outputs
