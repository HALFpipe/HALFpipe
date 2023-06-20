# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Any, Literal

result_keys = frozenset({"tags", "images", "vals", "metadata"})
ResultKey = Literal["tags", "images", "vals", "metadata"]

ResultDict = dict[ResultKey, dict[str, Any]]

# @final
# class ResultDict(TypedDict):
#     tags: dict[str, Any]
#     images: dict[str, Any]
#     vals: dict[str, Any]
#     metadata: dict[str, Any]
