# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .niftimetadata import NiftiheaderMetadataLoader
from .sidecar import SidecarMetadataLoader
from .database import DatabaseMetadataLoader


class MetadataLoader:
    def __init__(self, database):
        self.loaders = [
            SidecarMetadataLoader(),
            NiftiheaderMetadataLoader(self),
            DatabaseMetadataLoader(database, self),
        ]

    def fill(self, fileobj, key):
        if not hasattr(fileobj, "metadata"):
            fileobj.metadata = dict()
        if fileobj.metadata.get("key") is not None:
            return True
        for loader in self.loaders:
            if loader.fill(fileobj, key):
                return True
        return False
