# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from inflection import parameterize, camelize, underscore


def _replace_special(s):
    # replace gt and lt characters because these are confusing in bash later on
    s = s.replace("<>", " vs ")
    s = s.replace(">", " gt ")
    s = s.replace("<", " lt ")

    s = re.sub(r"\s+", " ", s)  # remove repeated whitespace

    return s


def format_like_bids(name):
    s = camelize(name)  # convert underscores to camel case
    s = re.sub(r"([A-Z])", r" \1", s)  # convert camel case into words

    s = _replace_special(s)

    s = underscore(parameterize(s))

    uppercase_first_letter = name[0].isupper()

    return camelize(s, uppercase_first_letter)


def format_workflow(s):
    s = re.sub(r"[_-]", " ", s)  # convert underscores to spaces
    s = re.sub(r"([A-Z]+)", r" \1", s)  # convert camel case into words

    s = _replace_special(s)

    return underscore(parameterize(s))
