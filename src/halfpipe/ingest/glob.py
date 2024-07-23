# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import fnmatch
import re
from os import path as op
from pathlib import Path
from typing import Callable, Container, Generator, Iterable

from ..utils.path import iterdir, rlistdir

tag_parse = re.compile(r"{(?P<tag_name>[a-z]+)((?P<filter_type>[:=])(?P<filter>(?:[^{}]|{\d+})+))?}")
tokenize = re.compile(r"(\A|[^\\])({[a-z]+(?:[:=](?:[^{}]|{\d+})+)?})")
magic_check = re.compile(r"(?:\*|\?|(?:\A|[^\\]){|[^\\]})")
special_match = re.compile(r"(\\[AbBdDsDwWZ])")
suggestion_match = re.compile(r"({suggestion(?:[:=][^}]+)?})")
chartype_filter = re.compile(r"(\[.+\])")
show_tag_suggestion_check = re.compile(r".*(?P<newtag>{(?P<tag_name>[a-z]*))(?P<newfilter>[:=][^}]+)?\Z")
remove_tag_remainder_match = re.compile(r"(?P<oldtag>[^}]*?})")


def tag_glob(
    pathname: str | Path, entities: Container[str] | None = None, dironly: bool = False
) -> Generator[tuple[str, dict[str, str]], None, None]:
    """
    adapted from cpython glob
    """
    dirname, basename = op.split(pathname)
    if not dirname:
        if is_recursive(basename):
            dir_generator = rlistdir(dirname, dironly)
        else:
            dir_generator = iterdir(dirname, dironly)
        for dirname in dir_generator:
            yield (dirname, dict())
        return
    if dirname != pathname and has_magic(dirname):
        dirs: Iterable[tuple[str, dict[str, str]]] = tag_glob(dirname, entities, dironly=True)
    else:
        dirs = [(dirname, dict())]
    for dirname, dirtagdict in dirs:
        for name, tagdict in _tag_glob_in_dir(dirname, basename, entities, dironly, dirtagdict):
            yield (op.join(dirname, name), _combine_tagdict(dirtagdict, tagdict))


def _combine_tagdict(a: dict[str, str], b: dict[str, str]) -> dict[str, str]:
    z = b.copy()
    for k, v in a.items():
        if k in z:
            assert v == z[k]
        else:
            z[k] = v
    return z


def _tag_glob_in_dir(
    dirname: str,
    basename: str,
    entities: Container[str] | None,
    dironly: bool,
    parenttagdict: dict[str, str],
):
    """
    adapted from cpython glob
    only basename can contain magic
    """
    assert not has_magic(dirname)
    fullmatch, entities = _translate(basename, entities, parenttagdict)
    for x in iterdir(dirname, dironly):
        matchobj = fullmatch(x)
        if matchobj is not None:
            yield (
                x,
                {
                    entity: value
                    for entity, value in matchobj.groupdict().items()
                    if entity in entities  # filter out groups added by fnmatch such as "g0"
                },
            )


def get_entities_in_path(pat: str) -> list[str]:
    res = []
    tokens = tokenize.split(pat)
    for token in tokens:
        if len(token) == 0:
            continue
        matchobj = tag_parse.fullmatch(token)
        if matchobj is not None:
            tag_name = matchobj.group("tag_name")
            res.append(tag_name)
    return res


def _validate_re(s: str) -> bool:
    try:
        re.compile(s)
        return True
    except Exception:
        pass
    return False


def _translate(pat: str, entities: Container[str] | None, parenttagdict: dict[str, str]) -> tuple[Callable, set[str]]:
    res = ""

    tokens = tokenize.split(pat)

    entities_in_res: set[str] = set()

    for token in tokens:
        if len(token) == 0:
            continue

        matchobj = tag_parse.fullmatch(token)
        if matchobj is not None:
            tag_name = matchobj.group("tag_name")
            if entities is None or tag_name in entities:
                filter_type = matchobj.group("filter_type")
                filter_str = matchobj.group("filter")

                if tag_name in parenttagdict:
                    s = parenttagdict[tag_name]
                    if s.endswith("/"):
                        s = s[:-1]
                    res += re.escape(s)
                    # TODO warning that filter is ignored
                    continue

                enre = None
                if filter_str is not None:
                    if filter_type == ":":
                        enre = filter_str.replace("\\{", "{").replace("\\}", "}")  # regex syntax
                    elif filter_type == "=":  # glob syntax
                        enre = fnmatch.translate(filter_str)
                        enre = special_match.sub("", enre)  # remove control codes

                if enre is None or not _validate_re(enre):
                    enre = r"[^/]+"

                if tag_name not in entities_in_res:
                    res += r"(?P<%s>%s)" % (tag_name, enre)
                    entities_in_res.add(tag_name)
                else:
                    res += r"(?P=%s)" % tag_name
            else:
                res += re.escape(token)

        else:
            fnre = fnmatch.translate(token)
            fnre = special_match.sub("", fnre)
            fnre = fnre.replace(".*", "[^/]*")
            res += fnre

    res += "/?"

    return re.compile(res).fullmatch, entities_in_res


def has_magic(s) -> bool:
    return magic_check.search(s) is not None


def is_recursive(pattern: str) -> bool:
    return pattern == "**"
