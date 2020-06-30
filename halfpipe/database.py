# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from hashlib import sha1
import json
from functools import lru_cache
import logging

from calamities.pattern import tag_glob, tag_parse, get_entities_in_path

from .spec import (
    TagsSchema,
    bold_entities,
    entity_aliases as aliases,
    tagnames,
    QualitycheckExcludeEntrySchema,
)
from .utils import first


def _resolve(tn):
    if tn in aliases:
        return aliases[tn]
    return tn


class Database:
    def __init__(self, files=[]):
        self.filepaths_by_tags = dict()
        self.tags_by_filepaths = dict()

        self.fileobj_by_filepaths = dict()

        self.tmplstr_by_filepaths = dict()
        self.filepaths_by_tmplstr = dict()

        self.tags_schema = TagsSchema()
        for file_obj in files:
            self.add_file_obj(file_obj)

    def __hash__(self):
        return hash(tuple(self.tags_by_filepaths.keys()))

    def sha1(self):
        hash = sha1()
        for filepath in self.tags_by_filepaths.keys():
            hash.update(filepath.encode())
        return hash.hexdigest()

    def add_file_obj(self, file_obj):
        othertagdict = self.tags_schema.dump(file_obj.tags)

        tagglobres = list(tag_glob(file_obj.path))

        if len(tagglobres) == 0:
            logging.getLogger("halfpipe").warning(
                f'No files found for query "{file_obj.path}", skipping'
            )

        tmplstr = tag_parse.sub("{\\g<tag_name>}", file_obj.path)
        if tmplstr not in self.filepaths_by_tmplstr:
            self.filepaths_by_tmplstr[tmplstr] = []

        for filepath, tagdict in tagglobres:
            if filepath in self.tags_by_filepaths:
                continue

            tagdict.update(othertagdict)
            tags_obj = self.tags_schema.load(tagdict)

            self.tags_by_filepaths[filepath] = tags_obj
            self.fileobj_by_filepaths[filepath] = file_obj

            self.tmplstr_by_filepaths[filepath] = tmplstr
            self.filepaths_by_tmplstr[tmplstr].append(filepath)

            for tagname in tagnames:
                tagval = getattr(tags_obj, tagname, None)
                self.set_file_tag(filepath, tagname, tagval)

    def set_file_tag(self, filepath, tagname, tagval):
        if tagval is None:
            return
        if tagname not in self.filepaths_by_tags:
            self.filepaths_by_tags[tagname] = dict()
        tagvaldict = self.filepaths_by_tags[tagname]
        if tagval not in tagvaldict:
            tagvaldict[tagval] = set()
        tagvaldict[tagval].add(filepath)

    def get(self, **filters):
        res = None
        for tagname, tagval in filters.items():
            tagname = _resolve(tagname)
            if tagname in self.filepaths_by_tags and tagval in self.filepaths_by_tags[tagname]:
                cur_set = self.filepaths_by_tags[tagname][tagval]
                if res is not None:
                    res &= cur_set
                else:
                    res = cur_set.copy()
            else:
                res = None
                break
        if res is None:
            return set()
        return res

    def filter(self, filepaths, **filters):
        res = set(filepaths)
        for tagname, tagval in filters.items():
            tagname = _resolve(tagname)
            cur_set = self.filepaths_by_tags[tagname][tagval]
            res &= cur_set
        return res

    def matches(self, filepath, **filters):
        for tagname, querytagval in filters.items():
            tagval = self.get_tagval(filepath, tagname)
            if tagval != querytagval:
                return False
        return True

    def get_associations(self, filepath, **filters):
        tagsobj = self.get_tags(filepath)
        if tagsobj is None:
            return
        if tagsobj.datatype != "func" or tagsobj.suffix != "bold":
            return
        res = self.get(**filters)
        for entity in bold_entities:
            if entity == "direction" and "direction" not in get_entities_in_path(
                self.tmplstr_by_filepaths[filepath]
            ):
                continue
            entity = _resolve(entity)
            tagval = getattr(tagsobj, entity)
            if tagval is None:
                continue
            cur_set = res & self.filepaths_by_tags[entity][tagval]
            if len(cur_set) > 0:
                res = cur_set
            if len(cur_set) == 1:
                break
        if len(res) == 1:
            return (res.pop(),)
        elif len(res) > 1:
            return tuple(res)

    def get_tagval(self, filepath, tagname):
        if isinstance(filepath, (list, tuple)):
            return [self.get_tagval(fp, tagname) for fp in filepath]
        tagsobj = self.tags_by_filepaths.get(filepath)
        if tagsobj is not None:
            return getattr(tagsobj, _resolve(tagname), None)

    def get_tagvaldict(self, entity):
        return self.filepaths_by_tags.get(_resolve(entity))

    def get_all_with_tag(self, entity):
        tagvaldict = self.filepaths_by_tags.get(_resolve(entity))
        if tagvaldict is None:
            return
        for tagval, filepaths in tagvaldict.items():
            if tagval is not None:
                yield from filepaths

    def get_tags(self, filepath):
        return self.tags_by_filepaths.get(filepath)

    def get_fileobj(self, filepath):
        return self.fileobj_by_filepaths.get(filepath)

    def get_tagval_set(self, tagname, filepaths=None):
        if not isinstance(tagname, str):
            return
        tagname = _resolve(tagname)
        if tagname not in self.filepaths_by_tags:
            return
        if filepaths is not None:
            if not isinstance(filepaths, set):
                filepaths = set(filepaths)
            return set(
                tagval
                for tagval, tagvalfilepaths in self.filepaths_by_tags[tagname].items()
                if not filepaths.isdisjoint(tagvalfilepaths)
            )
        else:
            return set(self.filepaths_by_tags[tagname].keys())

    def get_multi_tagval_set(self, tagnames, filepaths=None, prune=True):
        def prunefun(tn):
            tagval_set = self.get_tagval_set(tn, filepaths=filepaths)
            return tagval_set is not None and len(tagval_set) > 1

        if prune:
            tagnames = [tn for tn in tagnames if prunefun(tn)]
        resolvedtagnames = [_resolve(tn) for tn in tagnames]

        if filepaths is None:
            filepaths = self.tags_by_filepaths.keys()

        return (
            tagnames,
            set(
                tuple(
                    getattr(self.tags_by_filepaths[filepath], tn, None) for tn in resolvedtagnames
                )
                for filepath in filepaths
                if filepath in self.tags_by_filepaths
            ),
        )

    def get_tmplstr(self, filepaths):
        if isinstance(filepaths, str):
            return self.tmplstr_by_filepaths.get(filepaths)
        tmplstrset = set(self.tmplstr_by_filepaths.get(filepath) for filepath in filepaths)
        if len(tmplstrset) == 1:
            return first(tmplstrset)


def _set_in_hierarchy(dicthierarchy, entities, entry):
    entity = entities.pop()
    curval = getattr(entry, entity, None)
    if len(entities) == 0:
        dicthierarchy[curval] = True
    else:
        if curval not in dicthierarchy:
            dicthierarchy[curval] = dict()
        if isinstance(dicthierarchy[curval], dict):
            _set_in_hierarchy(dicthierarchy[curval], entities, entry)


@lru_cache(maxsize=128)
def init_qualitycheck_exclude_database_cached(qualitycheckexcludefile):
    return QualitycheckExcludeDatabase(qualitycheckexcludefile)


class QualitycheckExcludeDatabase:
    def __init__(self, qualitycheckexcludefile):
        with open(qualitycheckexcludefile, "r") as fp:
            qualitycheckexcludes = json.load(fp)
        assert isinstance(qualitycheckexcludes, list)
        schema = QualitycheckExcludeEntrySchema()

        self.excludedicthierarchy = dict()

        for qualitycheckexcludedict in qualitycheckexcludes:
            entry = schema.load(qualitycheckexcludedict)
            for i, entity in enumerate(bold_entities):  # order determines precedence
                if getattr(entry, entity, None) is not None:
                    break
            _set_in_hierarchy(self.excludedicthierarchy, bold_entities[i:], entry)

    def get(self, **kwargs):
        curdict = self.excludedicthierarchy
        for entity in bold_entities:
            curval = kwargs.get(entity)
            if curval not in curdict:
                return
            elif curdict[curval] is True:
                return True
            elif isinstance(curdict[curval], dict):
                curdict = curdict[curval]
        return False
