# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict

import numpy as np

from nipype.interfaces.base import traits, DynamicTraitedSpec, BaseInterfaceInputSpec, isdefined
from nipype.interfaces.io import add_traits, IOBase

from .base import ResultdictsOutputSpec
from ...model import entities, ResultdictSchema
from ...utils import ravel


def _aggregate_if_possible(inval):
    if isinstance(inval, (list, tuple)) and len(inval) > 0:
        if all(isinstance(val, float) for val in inval):
            return np.asarray(inval).mean()
        if all(isinstance(val, list) for val in inval):
            return _aggregate_if_possible(ravel(inval))
        if all(isinstance(val, (dict)) for val in inval):
            tpllist = [tuple(sorted(val.items())) for val in inval]
            return dict(_aggregate_if_possible(tpllist))
        try:
            invalset = set(inval)
            if len(invalset) == 1:
                (aggval,) = invalset
                return aggval
        except TypeError:  # cannot make set from inval type
            pass
    return inval


class AggregateResultdictsInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    across = traits.Str(desc="across which entity to aggregate")
    include = traits.Dict(
        traits.Str(),
        traits.List(traits.Str()),
        desc="include only resultdicts that have one of the allowed values for the respective key",
    )


class AggregateResultdicts(IOBase):
    input_spec = AggregateResultdictsInputSpec
    output_spec = ResultdictsOutputSpec

    def __init__(self, numinputs=0, **inputs):
        super(AggregateResultdicts, self).__init__(**inputs)
        self._numinputs = numinputs
        if numinputs >= 1:
            input_names = [f"in{i+1}" for i in range(numinputs)]
            add_traits(self.inputs, input_names)
        else:
            input_names = []

    def _list_outputs(self):
        outputs = self._outputs().get()

        inputs = ravel([getattr(self.inputs, f"in{i+1}") for i in range(self._numinputs)])

        across = self.inputs.across
        assert across in entities, f'Cannot aggregate across "{across}"'

        include = {}
        if isdefined(self.inputs.include):
            include = self.inputs.include

        aggdicts = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for resultdict in inputs:
            resultdict = ResultdictSchema().load(resultdict)
            assert isinstance(resultdict, dict)
            tags = resultdict["tags"]

            if across not in tags:
                continue

            if any(
                key not in tags or tags[key] not in allowedvalues
                for key, allowedvalues in include.items()
            ):
                continue

            t = tuple(
                (key, value)
                for key, value in tags.items()
                if key != across
                and not isinstance(value, (tuple, list))  # Ignore lists, as they only
                # will be there if we aggregated before, meaning that this is not
                # a tag that separates different results anymore.
                # This is important for example if we want have aggregated unequal numbers
                # of runs across subjects, but we still want to compare across subjects
            )
            t = tuple(sorted(t))

            for f, nested in resultdict.items():
                for k, v in nested.items():
                    aggdicts[t][f][k].append(v)

        resultdicts = []
        for tagtupl, listdict in aggdicts.items():
            tagdict = dict(tagtupl)
            resultdict = dict(tags=tagdict, vals=dict())
            resultdict.update(listdict)  # create combined resultdict
            for f in ["tags", "metadata", "vals"]:
                for key, value in resultdict[f].items():
                    if key in ["confounds_removal"]:  # convert fields that should stay a list to tuple
                        value = [tuple(v) for v in value]
                    resultdict[f][key] = _aggregate_if_possible(value)
                    if key in ["confounds_removal"]:
                        value = list(value)  # convert back
            schema = ResultdictSchema()
            validation_errors = schema.validate(resultdict)
            for f in ["tags", "metadata", "vals"]:
                if f in validation_errors:
                    for key in validation_errors[f]:
                        del resultdict[f][key]  # remove invalid fields
            resultdicts.append(schema.load(resultdict))

        outputs["resultdicts"] = resultdicts

        return outputs
