# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
"""

from pathlib import Path
from os.path import relpath

from nipype.interfaces import afni

from ...utils import splitext


class ReHo(afni.ReHo):
    """
    3dReHo supports paths up to 300 characters
    Sometimes we have longer paths
    Therefore, use a symlink
    """

    def _format_arg(self, name, spec, value):
        if name == "in_file" or name == "mask_file":
            stem, ext = splitext(value)

            valuepath = Path(value)
            relvaluepath = relpath(valuepath)

            symlinkpath = Path(f"{stem[:200]}{ext}")

            i = 0
            while symlinkpath.resolve() != valuepath:
                if symlinkpath.is_file() or symlinkpath.is_symlink():
                    symlinkpath = Path(f"{stem[:200]}{i:03d}{ext}")
                    i += 1
                else:
                    symlinkpath.symlink_to(relvaluepath)

            value = str(symlinkpath)

        return super(ReHo, self)._format_arg(name, spec, value)
