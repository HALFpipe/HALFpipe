# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def formatlist(l):
    from halfpipe.utils import inflect_engine

    return inflect_engine.join([f'"{v}"' for v in l], conj="or")


def cleaner(name):
    return "".join([x for x in name if x.isalnum()])


def formatlikebids(name):
    import re
    from inflection import parameterize, camelize, underscore

    formatted_name = name
    formatted_name = formatted_name.replace("<>", " vs ")
    formatted_name = formatted_name.replace(">", " gt ")
    formatted_name = formatted_name.replace("<", " lt ")
    formatted_name = re.sub(" +", " ", formatted_name)
    formatted_name = camelize(underscore(parameterize(formatted_name)), False)
    return formatted_name
