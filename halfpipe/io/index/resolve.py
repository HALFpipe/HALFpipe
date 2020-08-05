# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import logging

from marshmallow import EXCLUDE
import marshmallow.exceptions

from calamities.pattern import tag_glob, tag_parse, get_entities_in_path

import bids

bids.config.set_option("extension_initial_dot", True)  # noqa
from bids import BIDSLayout

from ...model import FileSchema, entities, entity_longnames
from ...utils import splitext

file_schema = FileSchema()
entity_shortnames = {v: k for k, v in entity_longnames.items()}


class ResolvedSpec:
    def __init__(self, spec):
        self.spec = spec

        self.fileobj_by_filepaths = dict()

        self.specfileobj_by_filepaths = dict()
        self.fileobjs_by_specfilepaths = dict()

        for fileobj in self.spec.files:
            self.resolve(fileobj)

    @property
    def resolved_files(self):
        yield from self.fileobj_by_filepaths.values()

    def put(self, fileobj):
        self.spec.put(fileobj)
        return self.resolve(fileobj)

    def _resolve_fileobj_with_tags(self, fileobj):
        tagglobres = list(tag_glob(fileobj.path))
        if len(tagglobres) == 0:
            logging.getLogger("halfpipe").warning(f'No files found for query "{fileobj.path}"')

        tmplstr = tag_parse.sub(
            "{\\g<tag_name>}", fileobj.path
        )  # remove regex information from path if present

        resolved_files = []

        for filepath, tagdict in tagglobres:
            filedict = file_schema.dump(fileobj)

            filedict["path"] = filepath
            _, filedict["extension"] = splitext(filepath)

            tagdict.update(filedict.get("tags", {}))
            filedict["tags"] = tagdict

            filedict["tmplstr"] = tmplstr

            resolved_fileobj = file_schema.load(filedict)

            self.fileobj_by_filepaths[filepath] = resolved_fileobj
            self.specfileobj_by_filepaths[resolved_fileobj.path] = fileobj

            resolved_files.append(resolved_fileobj)

        return resolved_files

    def _resolve_bids(self, fileobj):
        layout = BIDSLayout(fileobj.path, absolute_paths=True)

        resolved_files = []

        for filepath, obj in layout.get_files().items():

            entitydict = obj.get_entities()

            tags = dict()
            for k, v in entitydict.items():
                entity = entity_shortnames[k] if k in entity_shortnames else k
                if entity in entities:
                    tags[entity] = str(v)

            filedict = {
                "datatype": entitydict.get("datatype"),
                "suffix": entitydict.get("suffix"),
                "extension": entitydict.get("extension"),
                "path": filepath,
                "tags": tags,
                "metadata": obj.get_metadata()
            }

            try:
                resolved_fileobj = file_schema.load(filedict, unknown=EXCLUDE)

                self.fileobj_by_filepaths[filepath] = resolved_fileobj
                self.specfileobj_by_filepaths[resolved_fileobj.path] = fileobj

                resolved_files.append(resolved_fileobj)
            except marshmallow.exceptions.ValidationError as e:
                logging.getLogger("halfpipe.ui").warning(f'Ignored validation error in "{filepath}": %s', e, stack_info=True)

        return resolved_files

    def resolve(self, fileobj):
        if len(get_entities_in_path(fileobj.path)) == 0:
            if fileobj.datatype == "bids":
                resolved_files = self._resolve_bids(fileobj)
            else:
                resolved_files = [fileobj]
                self.fileobj_by_filepaths[fileobj.path] = fileobj
        else:
            resolved_files = self._resolve_fileobj_with_tags(fileobj)

        self.fileobjs_by_specfilepaths[fileobj.path] = resolved_files

        return resolved_files

    def fileobj(self, filepath):
        return self.fileobj_by_filepaths.get(filepath)

    def specfileobj(self, filepath):
        return self.specfileobj_by_filepaths.get(filepath)

    def fromspecfileobj(self, specfileobj):
        return self.fileobjs_by_specfilepaths.get(specfileobj.path)
