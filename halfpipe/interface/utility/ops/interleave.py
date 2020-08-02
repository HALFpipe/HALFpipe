# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from nipype.interfaces.base import (
    SimpleInterface,
    TraitedSpec,
    traits,
    isdefined
)


class InterleaveInputSpec(TraitedSpec):
    list1 = traits.List(traits.Any(), mandatory=True)
    indices1 = traits.List(traits.Int(), mandatory=True)
    list2 = traits.List(traits.Any(), mandatory=True)
    indices2 = traits.List(traits.Int())


class InterleaveOutputSpec(TraitedSpec):
    out_list = traits.List(traits.Any(), mandatory=True)


class Interleave(SimpleInterface):
    input_spec = InterleaveInputSpec
    output_spec = InterleaveOutputSpec

    def _run_interface(self, runtime):
        list1 = self.inputs.list1
        indices1 = self.inputs.indices1
        list2 = self.inputs.list2
        indices2 = self.inputs.indices2

        if not isdefined(indices2):
            indices2 = None

        else:
            indices2, list2 = map(list, zip(*sorted(zip(indices2, list2))))

        out_list = []
        for i, v in sorted(zip(indices1, list1)):
            print(i, len(out_list))
            while len(out_list) < i:
                if indices2 is not None:
                    assert len(out_list) == indices2.pop(0)
                out_list.append(list2.pop(0))
            out_list.append(v)

        self._results["out_list"] = out_list

        return runtime
