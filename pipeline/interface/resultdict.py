# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from copy import deepcopy
from shutil import copyfile
import logging
from pprint import pformat

from ..spec import bold_entities
from ..utils import ravel, splitext

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    DynamicTraitedSpec,
    BaseInterfaceInputSpec,
    SimpleInterface,
    isdefined,
)
from nipype.interfaces.io import add_traits, IOBase

filefields = ["preproc", "stat", "cope", "varcope", "zstat", "dof_file", "mask_file", "matrix"]


class MakeResultdictsInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    basedict = traits.Dict(traits.Str(), traits.Any())


class MakeResultdictsOutputSpec(TraitedSpec):
    resultdicts = traits.List(traits.Dict(traits.Str(), traits.Any()))


class MakeResultdicts(IOBase):
    input_spec = MakeResultdictsInputSpec
    output_spec = MakeResultdictsOutputSpec

    def __init__(self, keys=None, **inputs):  # filterdict=None,
        super(MakeResultdicts, self).__init__(**inputs)
        if keys is not None:
            add_traits(self.inputs, keys)
        else:
            keys = []
        self._keys = keys
        # self._filterdict = filterdict

    def _list_outputs(self):
        outputs = self._outputs().get()

        inputs = [getattr(self.inputs, key) for key in self._keys]
        maxlen = max(len(input) if isinstance(input, (list, tuple)) else 1 for input in inputs)

        for i in range(len(inputs)):
            if isinstance(inputs[i], tuple):
                inputs[i] = list(inputs[i])
            if not isinstance(inputs[i], list):
                inputs[i] = [inputs[i]]
            if len(inputs[i]) == 1:  # simple broadcasting
                inputs[i] *= maxlen
            if len(inputs[i]) == 0:
                inputs[i] = [None] * maxlen
            assert len(inputs[i]) == maxlen, "Can't broadcast lists"

        inputtupls = zip(*inputs)

        resultdicts = []
        for inputtupl in inputtupls:
            resultdict = deepcopy(self.inputs.basedict)
            for k, v in zip(self._keys, inputtupl):
                if v is not None:
                    resultdict[k] = v
            resultdicts.append(resultdict)

        # if self._filterdict is not None:
        #     filteredresultdicts = []
        #     for resultdict in resultdicts:
        #         include = True
        #         for key, filter in self._filterdict.items():
        #             if key not in resultdict:
        #                 continue
        #             if re.match(filter, resultdict[key]) is not None:
        #                 include = False
        #         if include:
        #             filteredresultdicts.append(resultdict)
        #     resultdicts = filteredresultdicts

        outputs["resultdicts"] = resultdicts

        return outputs


class AggregateResultdictsInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    across = traits.Str(desc="across which entity to aggregate")
    filter = traits.Dict(
        traits.Str(), traits.List(traits.Str()), desc="only select resultdicts that match"
    )


class AggregateResultdicts(IOBase):
    input_spec = AggregateResultdictsInputSpec
    output_spec = MakeResultdictsOutputSpec

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
        assert across in bold_entities

        filter = {}
        if isdefined(self.inputs.filter):
            filter = self.inputs.filter

        aggdict = {}
        for resultdict in inputs:
            if across not in resultdict:
                continue
            if any(
                key not in resultdict or resultdict[key] not in allowedvalues
                for key, allowedvalues in filter.items()
            ):
                continue
            tagtupl = tuple(
                (key, value)
                for key, value in resultdict.items()
                if key not in filefields
                and key != across
                and not isinstance(value, (tuple, list))  # if we aggregated before, ignore
                # this is important for example if we want have aggregated unequal numbers
                # of runs across subjects, but we still want to compare across subjects
            )
            if tagtupl not in aggdict:
                aggdict[tagtupl] = {}
            for key, value in resultdict.items():
                if isinstance(key, list):
                    key = tuple(key)  # need to be able to use this as key
                if (
                    key in filefields or key == across or isinstance(value, (list, tuple))
                ):  # the inverse of above
                    if key not in aggdict[tagtupl]:
                        aggdict[tagtupl][key] = []
                    aggdict[tagtupl][key].append(value)

        resultdicts = []
        for tagtupl, listdict in aggdict.items():
            resultdict = dict(tagtupl)
            resultdict.update(listdict)
            resultdicts.append(resultdict)

        outputs["resultdicts"] = resultdicts

        return outputs


class ExtractFromResultdictInputSpec(BaseInterfaceInputSpec):
    indict = traits.Dict(traits.Str(), traits.Any())


class ExtractFromResultdictOutputSpec(DynamicTraitedSpec):
    remainder = traits.Dict(traits.Str(), traits.Any())


class ExtractFromResultdict(IOBase):
    input_spec = ExtractFromResultdictInputSpec
    output_spec = ExtractFromResultdictOutputSpec

    def __init__(self, keys=[], aliases=None, **inputs):
        super(ExtractFromResultdict, self).__init__(**inputs)
        self._keys = keys
        self._aliases = aliases
        if self._aliases is None:
            self._aliases = {}

    def _add_output_traits(self, base):
        return add_traits(base, self._keys)

    def _list_outputs(self):
        outputs = self.output_spec().get()

        indict = self.inputs.indict

        outdict = dict()
        for key in self._keys:
            keys = [key]
            if key in self._aliases:
                keys.extend(self._aliases[key])
            for inkey in keys:
                if inkey in indict:
                    outdict[key] = indict[inkey]
                    del indict[inkey]
                    break

        for key in self._keys:
            if key in outdict:
                outputs[key] = outdict[key]
            else:
                outputs[key] = []

        for key in filefields:
            if key in indict:
                del indict[key]

        outputs["remainder"] = indict

        return outputs


class ResultdictDatasinkInputSpec(TraitedSpec):
    base_directory = traits.Directory(desc="Path to the base directory for storing data.")
    indicts = traits.List(traits.Dict(traits.Str(), traits.Any()))


class ResultdictDatasink(SimpleInterface):
    input_spec = ResultdictDatasinkInputSpec
    output_spec = TraitedSpec

    always_run = True

    def _run_interface(self, runtime):
        for resultdict in self.inputs.indicts:
            basepath = Path(self.inputs.base_directory)
            keys = set(resultdict.keys())
            for entity in reversed(bold_entities):
                if entity in keys and isinstance(resultdict[entity], str):
                    basepath = basepath.joinpath(f"_{entity}_{resultdict[entity]}_")
                    keys.remove(entity)
            newkeys = set()
            for entity in sorted(keys):
                if entity not in filefields and isinstance(resultdict[entity], str):
                    basepath = basepath.joinpath(f"_{entity}_{resultdict[entity]}_")
                else:
                    newkeys.add(entity)
            keys = newkeys
            basepath.mkdir(parents=True, exist_ok=True)
            for field in reversed(filefields):
                fieldvalue = resultdict.get(field)
                if isinstance(fieldvalue, str):
                    _, ext = splitext(fieldvalue)
                    outpath = basepath / f"{field}{ext}"
                    if outpath.exists():
                        logging.getLogger("pipeline").warning(f'Overwriting file "{outpath}"')
                    copyfile(fieldvalue, outpath)
                elif fieldvalue is not None:
                    pstr = pformat(fieldvalue)
                    logging.getLogger("pipeline").debug(f'Not copying "{pstr}"')

        return runtime
