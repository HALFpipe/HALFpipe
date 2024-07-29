# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .factory import Factory


class MriqcFactory(Factory):
    def __init__(self, ctx):
        super(MriqcFactory, self).__init__(ctx)

    def setup(self, workdir, boldfilepaths):
        raise NotImplementedError()

    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)  # type: ignore

    def connect(self, nodehierarchy, node, *args, **kwargs):
        return super().connect(nodehierarchy, node, *args, **kwargs)
