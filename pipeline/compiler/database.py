# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from calamities import tag_glob

from ..spec import (
    TagsSchema,
    scan_entities,
    entity_aliases as aliases,
)


def _resolve(tn):
    if tn in aliases:
        return aliases[tn]
    return tn


class Database:
    def __init__(self, files=[]):
        self.filepaths_by_tags = dict()
        self.tags_by_filepaths = dict()
        self.fileobj_by_filepaths = dict()

        self.tags_schema = TagsSchema()
        for file_obj in files:
            self.add_file(file_obj)

    def add_file_obj(self, file_obj):
        othertagdict = self.tags_schema.dump(file_obj.tags)
        tagglobres = tag_glob(file_obj.path)
        for filepath, tagdict in tagglobres:
            if filepath in self.tags_by_filepaths:
                continue
            tagdict.update(othertagdict)
            tags_obj = self.tags_schema.load(tagdict)
            self.tags_by_filepaths[filepath] = tags_obj
            self.fileobj_by_filepaths[filepath] = file_obj
            for tagname in tagdict.keys():
                tagval = getattr(tags_obj, tagname)
                if tagval is not None:
                    self.set_file_tag(filepath, tagname, tagval)

    def set_file_tag(self, filepath, tagname, tagval):
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
            if (
                tagname in self.filepaths_by_tags
                and tagval in self.filepaths_by_tags[tagname]
            ):
                cur_set = self.filepaths_by_tags[tagname][tagval]
                if res is not None:
                    res &= cur_set
                else:
                    res = cur_set.copy()
        return res

    def filter(self, filepaths, **filters):
        res = set(filepaths)
        for tagname, tagval in filters.items():
            tagname = _resolve(tagname)
            cur_set = self.filepaths_by_tags[tagname][tagval]
            res &= cur_set
        return res

    def get_events(self, filepath):
        tagsobj = self.get_tags(filepath)
        if tagsobj.datatype != "func" or tagsobj.suffix != "bold":
            return
        res = self.get(datatype="func", suffix="events")
        for entity in scan_entities:
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
            return res.pop()
        elif len(res) > 1:
            return tuple(res)

    def get_tagvaldict(self, entity):
        return self.filepaths_by_tags.get(_resolve(entity))

    def get_tags(self, filepath):
        return self.tags_by_filepaths.get(filepath)

    def get_fileobj(self, filepath):
        return self.fileobj_by_filepaths.get(filepath)

    def get_tags_set(self, filepaths, tagname):
        tagname = _resolve(tagname)
        if filepaths is not None and isinstance(tagname, str):
            return set(
                getattr(self.tags_by_filepaths[filepath], tagname)
                for filepath in filepaths
                if filepath in self.tags_by_filepaths
                and hasattr(self.tags_by_filepaths[filepath], tagname)
                and getattr(self.tags_by_filepaths[filepath], tagname) is not None
            )

    def get_multi_tags_set(self, filepaths, tagnames):
        tagnames = [
            tn
            for tn in tagnames
            if all(
                hasattr(self.tags_by_filepaths[filepath], _resolve(tn))
                and getattr(self.tags_by_filepaths[filepath], _resolve(tn)) is not None
                for filepath in filepaths
            )
        ]
        return (
            tagnames,
            set(
                tuple(
                    getattr(self.tags_by_filepaths[filepath], _resolve(tn))
                    for tn in tagnames
                )
                for filepath in filepaths
                if filepath in self.tags_by_filepaths
            ),
        )
