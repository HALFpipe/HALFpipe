# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.interfaces.base import traits

from ..transformer import Transformer, TransformerInputSpec


class RemoveVolumesInputSpec(TransformerInputSpec):
    skip_vols = traits.Int(mandatory=True)


class RemoveVolumes(Transformer):
    input_spec = RemoveVolumesInputSpec
    suffix = "cut"

    def _transform(self, array):
        array2 = array[self.inputs.skip_vols :, ...]
        return array2
