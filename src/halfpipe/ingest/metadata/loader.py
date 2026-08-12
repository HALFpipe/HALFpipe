# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from typing import TYPE_CHECKING

from ...model.file.base import File
from .base import Loader
from .database import DatabaseMetadataLoader
from .niftimetadata import NiftiheaderMetadataLoader

if TYPE_CHECKING:
    from ..database import Database


class MetadataLoader(Loader):
    def __init__(self, database: "Database") -> None:
        self.nifti_metadata_loader = NiftiheaderMetadataLoader(self)
        self.loaders: list[Loader] = [
            database.resolved_spec.sidecar_metadata_loader,
            self.nifti_metadata_loader,
            DatabaseMetadataLoader(database, self),
        ]

    def fill(self, fileobj: File, key: str) -> bool:
        if not hasattr(fileobj, "metadata"):
            fileobj.metadata = dict()
        if fileobj.metadata.get("key") is not None:
            return True

        if key == "slice_timing" and "slice_timing_code" in fileobj.metadata:
            # slice_timing_code takes precedence
            # slice_timing_code is translated by the NiftiheaderMetadataLoader
            # so we run it first here
            if self.nifti_metadata_loader.fill(fileobj, key):
                return True

        for loader in self.loaders:
            if loader.fill(fileobj, key):
                return True

        return False
