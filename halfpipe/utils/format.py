# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def formatlist(in_list):
    from halfpipe.utils import inflect_engine

    return inflect_engine.join([f'"{v}"' for v in in_list], conj="or")


def cleaner(name):
    return "".join([x for x in name if x.isalnum()])


def formatlikebids(name):
    import re
    from inflection import parameterize, camelize, underscore

    formatted_name = camelize(name)  # convert underscores to camel case
    formatted_name = re.sub(r"([A-Z])", r" \1", formatted_name)  # convert camel case into words

    # replace gt and lt characters because these are confusing in bash later on
    formatted_name = formatted_name.replace("<>", " vs ")
    formatted_name = formatted_name.replace(">", " gt ")
    formatted_name = formatted_name.replace("<", " lt ")

    formatted_name = re.sub(r"\s+", " ", formatted_name)  # remove repeated whitespace

    uppercase_first_letter = name[0].isupper()

    formatted_name = camelize(
        underscore(parameterize(formatted_name)),
        uppercase_first_letter
    )  # format

    return formatted_name
