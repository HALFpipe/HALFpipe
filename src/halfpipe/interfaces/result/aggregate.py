# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import BaseInterfaceInputSpec, DynamicTraitedSpec, traits
from nipype.interfaces.io import IOBase, add_traits

from ...result.aggregate import aggregate_results
from ...utils.ops import ravel
from .base import ResultdictsOutputSpec


class AggregateResultdictsInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    across = traits.Str(desc="across which entity to aggregate")


class AggregateResultdictsOutputSpec(ResultdictsOutputSpec):
    non_aggregated_resultdicts = traits.List(traits.Dict(traits.Str(), traits.Any()))


class AggregateResultdicts(IOBase):
    input_spec = AggregateResultdictsInputSpec
    output_spec = AggregateResultdictsOutputSpec

    def __init__(self, numinputs=0, **inputs):
        super(AggregateResultdicts, self).__init__(**inputs)
        self._numinputs = numinputs
        if numinputs >= 1:
            self.input_names = [f"in{i+1}" for i in range(numinputs)]
            add_traits(self.inputs, self.input_names)
        else:
            self.input_names = []

    def _list_outputs(self):
        outputs = self._outputs()
        assert outputs is not None
        outputs = outputs.get()

        inputs = list()
        for result in ravel([getattr(self.inputs, input_name) for input_name in self.input_names]):
            if isinstance(result, dict):
                inputs.append(result)
            else:
                raise ValueError(f'Cannot handle input "{result}"')

        across = self.inputs.across

        aggregated, non_aggregated = aggregate_results(inputs, across)

        outputs["resultdicts"] = aggregated
        outputs["non_aggregated_resultdicts"] = non_aggregated

        return outputs
