# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from hashlib import sha1

from .resolve import ResolvedSpec
from ..metadata import MetadataLoader
from ...model.tags import entities
from ...utils import first


class Database:
    def __init__(self, spec):
        resolved_spec = None
        if isinstance(spec, ResolvedSpec):
            resolved_spec = spec
        if resolved_spec is None:
            resolved_spec = ResolvedSpec(spec)
        self.resolved_spec = resolved_spec

        self.metadata_loader = MetadataLoader(self)

        self.filepaths_by_tags = dict()
        self.tags_by_filepaths = dict()

        for file_obj in self.resolved_spec.resolved_files:
            self.index(file_obj)

    def __hash__(self):
        return hash(tuple(self.tags_by_filepaths.keys()))

    @property
    def sha1(self):
        hash = sha1()
        for filepath in self.tags_by_filepaths.keys():
            hash.update(filepath.encode())
        return hash.hexdigest()

    def put(self, spec_fileobj):
        resolved_files = self.resolved_spec.put(spec_fileobj)
        for resolved_fileobj in resolved_files:
            self.index(resolved_fileobj)

    def index(self, fileobj):
        def add_tag_to_index(filepath, entity, tagval):
            if tagval is None:
                return

            if entity not in self.filepaths_by_tags:
                self.filepaths_by_tags[entity] = dict()
            tagvaldict = self.filepaths_by_tags[entity]

            if tagval not in tagvaldict:
                tagvaldict[tagval] = set()
            tagvaldict[tagval].add(filepath)

        filepath = fileobj.path

        tags = dict()
        if hasattr(fileobj, "tags"):
            tags = fileobj.tags

        tagdict = dict(datatype=fileobj.datatype)
        tagdict.update(tags)
        if hasattr(fileobj, "suffix"):
            tagdict.update(dict(suffix=fileobj.suffix))
        if hasattr(fileobj, "extension"):
            tagdict.update(dict(extension=fileobj.extension))

        self.tags_by_filepaths[filepath] = dict(**tagdict)

        if hasattr(fileobj, "intended_for"):
            intended_for = fileobj.intended_for
            for k, newvaluelist in intended_for.items():
                from_entity, from_tagval = k.split(".")

                if from_tagval == "null":
                    from_tagval = None

                tagval = tagdict.get(from_entity)
                if tagval != from_tagval:
                    continue

                if from_entity in tagdict:
                    del tagdict[from_entity]  # not indexable by old tag

                for v in newvaluelist:
                    to_entity, to_tagval = v.split(".")
                    add_tag_to_index(filepath, to_entity, to_tagval)

        for tagname, tagval in tagdict.items():
            add_tag_to_index(filepath, tagname, tagval)

    def tags(self, filepath):
        """
        get a dictionary of entity -> value for a specific filepath
        """
        return self.tags_by_filepaths.get(filepath)

    def fileobj(self, filepath):
        return self.resolved_spec.fileobj(filepath)

    def specfileobj(self, filepath):
        return self.resolved_spec.specfileobj(filepath)

    def fromspecfileobj(self, specfileobj):
        return self.resolved_spec.fromspecfileobj(specfileobj)

    def tagval(self, filepath, entity):
        if isinstance(filepath, (list, tuple)):  # vectorize
            return [self.tagval(fp, entity) for fp in filepath]
        tagdict = self.tags_by_filepaths.get(filepath)
        if tagdict is not None:
            return tagdict.get(entity)

    def tagvaldict(self, entity):
        return self.filepaths_by_tags.get(entity)

    def get(self, **filters):
        res = None
        for tagname, tagval in filters.items():
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

        for entity, tagval in filters.items():
            cur_set = self.filepaths_by_tags[entity][tagval]
            res &= cur_set

        return res

    def applyfilters(self, filepaths, filters):
        if not isinstance(filters, (tuple, list)) and hasattr(filters, "filters"):
            return self.applyfilters(filepaths, filters.filters)

        res = set(filepaths)

        for filter in filters:
            type = filter.get("type")
            if type == "tag":
                entity = filter.get("entity")
                assert entity in entities

                values = filter.get("values")
                assert isinstance(values, (list, tuple))

                filterset = set()
                for value in values:
                    filterset |= self.filter(filepaths, **{entity: value})

                action = filter.get("action")

                if action == "include":
                    res &= filterset
                elif action == "exclude":
                    res -= filterset
                else:
                    raise ValueError(f'Unsupported filter action "{action}"')

            else:
                raise ValueError(f'Unsupported filter type "{type}"')

        return res

    def matches(self, filepath, **filters):
        for entity, querytagval in filters.items():
            tagval = self.tagval(filepath, entity)
            if tagval != querytagval:
                return False
        return True

    def associations(self, filepath, **filters):
        res = self.get(**filters)
        for entity in reversed(entities):  # from high to low priority
            if entity not in self.filepaths_by_tags:
                continue
            cur_set = set()
            for _, filepaths in self.filepaths_by_tags[entity].items():
                if filepath in filepaths:
                    cur_set |= set(filepaths)
            cur_set &= res
            if len(cur_set) > 0:
                res = cur_set
            if len(cur_set) == 1:
                break
        if len(res) > 0:
            return tuple(res)

    def tagvalset(self, entity, filepaths=None):
        if not isinstance(entity, str):
            return
        if entity not in self.filepaths_by_tags:
            return
        if filepaths is not None:
            if not isinstance(filepaths, set):
                filepaths = set(filepaths)
            return set(
                tagval
                for tagval, tagvalfilepaths in self.filepaths_by_tags[entity].items()
                if not filepaths.isdisjoint(tagvalfilepaths)
            )
        else:
            return set(self.filepaths_by_tags[entity].keys())

    def multitagvalset(self, entitylist, filepaths=None, prune=True):
        if prune:
            pruned_entitylist = []
            for entity in entitylist:
                tagval_set = self.tagvalset(entity, filepaths=filepaths)
                if tagval_set is not None and len(tagval_set) > 1:
                    pruned_entitylist.append(entity)
            entitylist = pruned_entitylist

        if filepaths is None:
            filepaths = self.tags_by_filepaths.keys()

        return (
            entitylist,
            set(
                tuple(self.tags_by_filepaths[filepath].get(entity) for entity in entitylist)
                for filepath in filepaths
                if filepath in self.tags_by_filepaths
            ),
        )

    def tmplstr(self, filepaths):
        if isinstance(filepaths, str):
            return self.fileobj(filepaths).tmplstr
        tmplstrset = set(self.tmplstr(filepath) for filepath in filepaths)
        if len(tmplstrset) == 1:
            return first(tmplstrset)

    def fillmetadata(self, key, filepaths):
        found = False
        found_all = True
        for filepath in filepaths:
            fileobj = self.fileobj(filepath)
            if fileobj is None:
                raise ValueError(f"Unknown filepath \"{filepath}\"")
            found = self.metadata_loader.fill(fileobj, key)
            found_all = found_all and found
        return found

    def metadata(self, filepath, key):
        fileobj = self.fileobj(filepath)
        if fileobj is not None and hasattr(fileobj, "metadata"):
            if fileobj.metadata is not None and isinstance(fileobj.metadata, dict):
                return fileobj.metadata.get(key)

    def metadatavalset(self, key, filepaths):
        valset = set()
        for filepath in filepaths:
            valset.add(self.metadata(filepath, key))

        return valset
