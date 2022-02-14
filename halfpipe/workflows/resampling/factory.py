# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe

from .alt import init_alt_bold_std_trans_wf

from ..factory import Factory
from ..memory import MemoryCalculator, patch_mem_gb


class AltBOLDFactory(Factory):
    def __init__(self, ctx, fmriprep_factory):
        super(AltBOLDFactory, self).__init__(ctx)

        self.previous_factory = fmriprep_factory

    def setup(self):
        prototype = init_alt_bold_std_trans_wf()
        self.wf_name = prototype.name

    def get(self, sourcefile, **_):
        hierarchy = self._get_hierarchy("settings_wf", sourcefile=sourcefile)
        wf = hierarchy[-1]

        vwf = wf.get_node(self.wf_name)
        connect = False

        if vwf is None:
            connect = True

            memcalc = MemoryCalculator.from_bold_file(sourcefile)
            vwf = init_alt_bold_std_trans_wf(memcalc=memcalc)

            for node in vwf._get_all_nodes():
                patch_mem_gb(node, memcalc)

            wf.add_nodes([vwf])

        inputnode = vwf.get_node("inputnode")
        assert isinstance(inputnode, pe.Node)
        hierarchy.append(vwf)

        if connect:
            self.previous_factory.connect(hierarchy, inputnode, sourcefile=sourcefile)

        outputnode = vwf.get_node("outputnode")

        return hierarchy, outputnode
