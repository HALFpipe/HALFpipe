# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import fnmatch
import os
import re
from os import path as op
from pathlib import Path
from threading import Event
from typing import Callable, Container, Generator, Iterable

import inflect

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
            full_name = op.join(dirname, name)
            if not op.exists(full_name):
                continue
            yield (full_name, _combine_tagdict(dirtagdict, tagdict))


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


# the Config, resolve and get_dir are from ui.components, I would take them out and put here
# and then reroute all references to them to here
class Config:
    fs_root: str = "/"


def get_dir(text):
    if text is None:
        dir = os.curdir
    else:
        dir = op.dirname(text)
    if len(dir) == 0:
        dir = os.curdir
    return dir


def resolve(path) -> str:
    abspath = op.abspath(path)

    fs_root = Config.fs_root

    if not abspath.startswith(fs_root):
        abspath = fs_root + abspath

    return op.normpath(abspath)


def _is_candidate(filepath, dironly):
    if dironly is True:
        return op.isdir(filepath)
    else:
        return op.isfile(filepath)


def _scan_files_and_collect_tags(
    newpathname: str, schema_entities: list[str], dironly: bool, _scan_requested_event: Event, logger=None
) -> tuple[set[str], list[str], dict] | None:
    """
    Scans files using tag_glob and collects suggestions, valid file paths, and tag dictionaries.

    Parameters
    ----------
    newpathname : str
        The path pattern to search.
    schema_entities : list[str]
        The list of schema-related tag entities.
    dironly : bool
        Whether to only consider directories.
    _scan_requested_event : Event
        An event used to signal that the scan should stop early.

    Returns
    -------
    tuple[set[str], list[str], list[dict]]
        A set of suggestion strings, a list of valid file paths, and a list of corresponding tag dictionaries.
    """

    tag_glob_generator = tag_glob(newpathname, schema_entities + ["suggestion"], dironly)

    new_suggestions = set()
    suggestiontempl = op.basename(newpathname)
    filepaths = []
    tagdictlist = []

    try:
        for filepath, tagdict in tag_glob_generator:
            if "suggestion" in tagdict and len(tagdict["suggestion"]) > 0:
                suggestionstr = suggestion_match.sub(tagdict["suggestion"], suggestiontempl)
                if op.isdir(filepath):
                    suggestionstr = op.join(suggestionstr, "")  # add trailing slash
                new_suggestions.add(suggestionstr)

            elif _is_candidate(filepath, dironly):
                filepaths.append(filepath)
                tagdictlist.append(tagdict)

            if _scan_requested_event.is_set():
                break

    except ValueError as e:
        if logger is not None:
            logger.debug("Error scanning files: %s", e, exc_info=True)
        pass
    except AssertionError as e:
        if logger is not None:
            logger.debug("Error scanning files: %s", e, exc_info=True)
        return None

    tagsetdict = {}
    if len(tagdictlist) > 0:
        tagsetdict = {k: set(dic[k] for dic in tagdictlist) for k in tagdictlist[0] if k != "suggestion"}

    return (new_suggestions, filepaths, tagsetdict)


def resolve_path_wildcards(newpathname: str) -> tuple[str, list[str]]:
    """
    Evaluates how many and what files were found based on the provided file pattern.

    This function takes a file pattern as input and uses globbing to find
    matching files. It returns a message indicating the number of files
    found and a list of the file paths. Possible TODO to make it simpler.

    Parameters
    ----------
    newpathname : str
        The file pattern to evaluate.

    Returns
    -------
    tuple[str, list[str]]
        A tuple containing:
        - A message indicating the number of files found and any
          associated tags.
        - A list of file paths that match the pattern.
    """

    from threading import Event

    # all possible entities
    schema_entities = ["subject", "task", "session", "run", "acquisition", "atlas", "seed", "map", "desc"]
    dironly = False

    # empty string gives strange behaviour!
    newpathname = newpathname if newpathname != "" else "/"
    scan_result = _scan_files_and_collect_tags(newpathname, schema_entities, dironly, Event())

    if scan_result is not None:
        new_suggestions, filepaths, tagsetdict = scan_result

    nfile = len(filepaths)

    p = inflect.engine()
    value = p.inflect(f"Found {nfile} plural('file', {nfile})")

    if len(tagsetdict) > 0:
        value += " "
        value += "for"
        value += " "
        tagmessages = [p.inflect(f"{len(v)} plural('{k}', {len(v)})") for k, v in tagsetdict.items()]
        value += p.join(tagmessages)

    return value, filepaths
