# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from typing import Mapping

from inflect import engine
from inflection import camelize, parameterize, underscore

from ..model.tags import entities, entity_longnames

inflect_engine = engine()
del engine


def normalize_subject(s) -> str:
    s = str(s)

    if s.startswith("sub-"):
        s = s[4:]

    return format_like_bids(s)


def _replace_special(s):
    # replace gt and lt characters because these are confusing in bash later on
    s = s.replace("<>", " vs ")
    s = s.replace(">", " gt ")
    s = s.replace("<", " lt ")

    s = re.sub(r"\s+", " ", s)  # remove repeated whitespace

    return s


def format_like_bids(name: str) -> str:
    if len(name) == 0:
        return name

    s = camelize(name)  # convert underscores to camel case
    s = re.sub(r"([A-Z])", r" \1", s)  # convert camel case into words

    s = _replace_special(s)

    s = underscore(parameterize(s))

    has_upper_first_letter = name[0].isupper()
    return camelize(s, has_upper_first_letter)


def format_workflow(s: str) -> str:
    if len(s) == 0:
        return s

    s = re.sub(r"[_-]", " ", s)  # convert underscores to spaces
    s = re.sub(r"([A-Z]+)", r" \1", s)  # convert camel case into words

    s = _replace_special(s)

    return underscore(parameterize(s))


def format_tags(tags: Mapping[str, str]) -> str:
    s = []

    for entity in reversed(entities):
        if entity in tags:
            value = tags[entity]

            entity = entity_longnames.get(entity, entity)

            s.append(f'{entity}="{value}"')

    return inflect_engine.join(s)
