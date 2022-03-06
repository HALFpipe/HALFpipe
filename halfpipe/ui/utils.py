# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re

from inflection import camelize, parameterize, underscore

from ..utils import inflect_engine as p

forbidden_chars = re.compile(r"[^a-zA-Z0-9_\-<> ]")

entity_colors = {
    "sub": "ired",
    "ses": "igreen",
    "run": "imagenta",
    "task": "icyan",
    "dir": "iyellow",
    "condition": "yellow",
    "desc": "yellow",
    "acq": "icyan",
    "echo": "yellow",
}


def makenamesuggestion(*words, index=None):
    suggestion = " ".join(words)
    suggestion = camelize(underscore(parameterize(suggestion)), False)
    suggestion = forbidden_chars.sub("", suggestion)
    if index is not None:
        suggestion = f"{suggestion}{index}"
    return suggestion


def messagefun(database, filetype, filepaths, tagnames, entity_display_aliases=dict()):
    message = ""
    if filepaths is not None:
        message = p.inflect(
            f"Found {len(filepaths)} {filetype} plural('file', {len(filepaths)})"
        )
        if len(filepaths) > 0:
            n_by_tag = dict()
            for tagname in tagnames:
                tagvalset = database.tagvalset(tagname, filepaths=filepaths)
                if tagvalset is not None:
                    n_by_tag[tagname] = len(tagvalset)
            tagmessages = [
                p.inflect(
                    f"{n} plural('{entity_display_aliases.get(tagname, tagname)}', {n})"
                )
                for tagname, n in n_by_tag.items()
                if n > 0
            ]
            message += " "
            message += "for"
            message += " "
            message += p.join(tagmessages)
    return message
