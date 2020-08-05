# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .direction import canonicalize_direction_code, parse_direction_str
from ...utils import first


class DatabaseMetadataLoader:
    def __init__(self, database, provider):
        self.database = database
        self.provider = provider

    def fill(self, fileobj, key):
        if self.database is None:
            return False

        value = None

        if key == "phase_encoding_direction":
            dir = fileobj.tags.get("dir")
            if dir is not None:
                try:
                    pedir_code = parse_direction_str(dir)
                    value = canonicalize_direction_code(pedir_code)
                except Exception:
                    pass

        if key == "echo_time_difference":  # calculate from associated files
            if fileobj.datatype == "fmap" and fileobj.suffix == "phasediff":
                filepath = fileobj.path
                magnitude1 = self.database.associations(filepath, suffix="magnitude1")
                magnitude2 = self.database.associations(filepath, suffix="magnitude2")
                if len(magnitude1) > 0 and len(magnitude2) > 0:
                    m1 = self.database.fileobj(first(magnitude1))
                    m2 = self.database.fileobj(first(magnitude2))
                    if self.provider.fill(m1, "echo_time") and self.provider.fill(m2, "echo_time"):
                        e1 = m1.metadata.get("echo_time")
                        e2 = m2.metadata.get("echo_time")
                        if e1 is not None and e2 is not None:
                            value = abs(e1 - e2)

        if value is None:
            return False

        fileobj.metadata[key] = value
        return True
