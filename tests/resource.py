# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from halfpipe import resource

data_dir = Path(__file__).parent / "data"
resource.register(data_dir)


def get(file_name: str | Path) -> str:
    return resource.get(file_name)


def setup():
    resource.register(data_dir)
