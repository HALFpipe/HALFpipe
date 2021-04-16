# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from .direction import canonicalize_direction_code, parse_direction_str
from ...utils import first, logger


class DatabaseMetadataLoader:
    def __init__(self, database, loader):
        self.database = database
        self.loader = loader

    def fill(self, fileobj, key):
        if self.database is None:
            return False

        value = None

        if key == "phase_encoding_direction":
            direction = fileobj.tags.get("dir")
            if direction is not None:
                try:
                    pedir_code = parse_direction_str(direction)
                    value = canonicalize_direction_code(pedir_code, fileobj.path)
                except Exception as e:
                    logger.warning(
                        "Ignored exception when loading phase_encoding_direction:",
                        exc_info=e,
                    )

        if key == "echo_time_difference":  # calculate from associated files
            if fileobj.datatype == "fmap" and fileobj.suffix == "phasediff":
                filepath = fileobj.path
                magnitude1 = self.database.associations(filepath, suffix="magnitude1")
                magnitude2 = self.database.associations(filepath, suffix="magnitude2")
                if magnitude1 is not None and magnitude2 is not None:
                    if len(magnitude1) > 0 and len(magnitude2) > 0:  # two magnitude files
                        m1 = self.database.fileobj(first(magnitude1))
                        m2 = self.database.fileobj(first(magnitude2))
                        if self.loader.fill(m1, "echo_time") and self.loader.fill(m2, "echo_time"):
                            e1 = m1.metadata.get("echo_time")
                            e2 = m2.metadata.get("echo_time")
                            if e1 is not None and e2 is not None:
                                value = abs(e1 - e2)

        if key == "echo_time":  # calculate from associated file
            if fileobj.datatype == "fmap" and fileobj.suffix.startswith("phase"):
                filepath = fileobj.path
                suffix = dict(phase1="magnitude1", phase2="magnitude2").get(fileobj.suffix)
                if suffix is not None:
                    magnitude = self.database.associations(filepath, suffix=suffix)
                    if magnitude is not None and len(magnitude) > 0:
                        m = self.database.fileobj(first(magnitude))
                        if self.loader.fill(m, "echo_time"):
                            value = m.metadata.get("echo_time")

        if value is None:
            return False

        fileobj.metadata[key] = value
        return True
