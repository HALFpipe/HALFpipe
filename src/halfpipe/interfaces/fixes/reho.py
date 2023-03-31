# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os.path import relpath
from pathlib import Path

from nipype.interfaces import afni

from ...utils.path import split_ext


class ReHo(afni.ReHo):
    """
    3dReHo supports paths up to 300 characters
    Sometimes we have longer paths
    Therefore, use a symlink
    """

    def _format_arg(self, name, spec, value):
        if name == "in_file" or name == "mask_file":
            stem, ext = split_ext(value)

            path = Path(value)
            relative_path = relpath(path)

            link_path = Path(f"{stem[:200]}{ext}")

            i = 0
            while link_path.resolve() != path:
                if link_path.is_file() or link_path.is_symlink():
                    link_path = Path(f"{stem[:200]}{i:03d}{ext}")
                    i += 1
                else:
                    link_path.symlink_to(relative_path)

            value = str(link_path)

        return super(ReHo, self)._format_arg(name, spec, value)
