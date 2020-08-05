# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..factory import Factory


class AnatReportsFactory(Factory):
    def __init__(self, spec, bidsdatabase, workflow, fmriprep_factory):
        super(AnatReportsFactory, self).__init__(spec, bidsdatabase, workflow)


class BoldReportsFactory(Factory):
    def __init__(self, spec, bidsdatabase, workflow, fmriprep_factory):
        super(BoldReportsFactory, self).__init__(spec, bidsdatabase, workflow)
