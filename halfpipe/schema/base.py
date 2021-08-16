# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Union

import os

from marshmallow import Schema

PathLike = Union[os.PathLike, str]


class BaseSchema(Schema):
    class Meta:
        ordered = True
