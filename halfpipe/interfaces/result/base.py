# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import TraitedSpec, traits


class ResultdictsOutputSpec(TraitedSpec):
    resultdicts = traits.List(traits.Dict(traits.Str(), traits.Any()))
