# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe

from ..factory import Factory
from ..fmriprep import FmriprepFactory
from ..memory import MemoryCalculator
from .alt import init_alt_bold_std_trans_wf


class AltBOLDFactory(Factory):
    """
    Factory for the alt_bold_std_trans_wf
    """

    def __init__(self, ctx, fmriprep_factory: FmriprepFactory) -> None:
        super(AltBOLDFactory, self).__init__(ctx)

        self.previous_factory = fmriprep_factory

    def setup(self) -> None:
        prototype = init_alt_bold_std_trans_wf()
        self.wf_name = prototype.name

    def get(self, source_file, **_):
        hierarchy = self._get_hierarchy("settings_wf", source_file=source_file)
        wf = hierarchy[-1]

        vwf = wf.get_node(self.wf_name)
        connect = False

        if vwf is None:
            connect = True

            memcalc = MemoryCalculator.from_bold_file(source_file)
            vwf = init_alt_bold_std_trans_wf(memcalc=memcalc)

            wf.add_nodes([vwf])

        assert isinstance(vwf, pe.Workflow)
        inputnode = vwf.get_node("inputnode")
        assert isinstance(inputnode, pe.Node)
        hierarchy.append(vwf)

        if connect:
            self.previous_factory.connect(hierarchy, inputnode, source_file=source_file)

        outputnode = vwf.get_node("outputnode")

        return hierarchy, outputnode
