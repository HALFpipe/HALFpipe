# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from os.path import relpath
from inflection import camelize
import json

from ...model import FileSchema, entity_longnames, entities
from ...utils import formatlikebids, splitext, cleaner

from bids.layout import Config
from bids.layout.writing import build_path
import bids.config

bids.config.set_option("extension_initial_dot", True)
bidsconfig = Config.load("bids")

bidsversion = "1.4.0"


class BidsDatabase:
    def __init__(self, database):
        self.database = database

        self.bidspaths_by_filepaths = dict()
        self.filepaths_by_bidspaths = dict()

        self.bidstags_by_bidspaths = dict()

    def _format_tagval(self, entity, v):
        if entity == "sub" or entity == "subject":
            return cleaner(v)
        return formatlikebids(v)

    def put(self, filepath):
        if self.bidspaths_by_filepaths.get(filepath) is not None:
            return  # already added
        tags = self.database.tags(filepath)
        bidstags = dict()
        for k, v in tags.items():
            bidsentity = k
            if bidsentity in entity_longnames:
                bidsentity = entity_longnames[bidsentity]
            if k in entities:
                bidstags[bidsentity] = self._format_tagval(k, v)
            else:
                if k == "suffix" and tags.get("datatype") == "fmap":
                    k = "fmap"
                bidstags[k] = v
        bidspath = build_path(bidstags, bidsconfig.default_path_patterns)
        self.bidspaths_by_filepaths[filepath] = str(bidspath)
        self.filepaths_by_bidspaths[bidspath] = str(filepath)
        self.bidstags_by_bidspaths[bidspath] = bidstags

    def tobids(self, filepath):
        return self.bidspaths_by_filepaths.get(filepath)

    def frombids(self, bidspath):
        return self.filepaths_by_bidspaths.get(bidspath)

    def tags(self, bidspath):
        """
        get a dictionary of entity -> value for a specific bidspath
        """
        return self.bidstags_by_bidspaths.get(bidspath)

    def tagval(self, bidspath, entity):
        if isinstance(bidspath, (list, tuple)):  # vectorize
            return [self.tagval(fp, entity) for fp in bidspath]
        tagdict = self.bidstags_by_bidspaths.get(bidspath)
        if tagdict is not None:
            return tagdict.get(entity)

    def write(self, bidsdir):
        bidsdir = Path(bidsdir)
        if bidsdir.is_symlink():
            raise ValueError("Will not write to symlink")
        bidsdir.mkdir(parents=True, exist_ok=True)

        dataset_description = {
            "Name": self.database.sha1,
            "BIDSVersion": bidsversion,
            "DatasetType": "raw"
        }
        with open(bidsdir / "dataset_description.json", "w") as f:
            json.dump(dataset_description, f, indent=4)

        for bidspath, filepath in self.filepaths_by_bidspaths.items():
            bidspath = Path(bidsdir) / bidspath
            bidspath.parent.mkdir(parents=True, exist_ok=True)
            if bidspath.is_file():
                continue  # ignore real files
            elif bidspath.is_symlink():
                if bidspath.resolve() == Path(filepath).resolve():
                    continue  # nothing to be done
                else:
                    bidspath.unlink()  # symlink points to different file
            relfilepath = relpath(filepath, start=bidspath.parent)
            bidspath.symlink_to(relfilepath)
            schema = FileSchema
            while hasattr(schema, "type_field") and hasattr(schema, "type_schemas"):
                v = self.database.tagval(filepath, schema.type_field)
                schema = schema.type_schemas[v]
            instance = schema()
            if "metadata" in instance.fields:
                metadata_keys = list(instance.fields["metadata"].nested().fields.keys())
                bidsmetadata = dict()
                task = self.database.tagval(filepath, "task")
                if task is not None:
                    bidsmetadata["TaskName"] = task
                for k in metadata_keys:
                    self.database.fillmetadata(k, [filepath])
                    v = self.database.metadata(filepath, k)
                    if v is not None:
                        bidsk = camelize(k)
                        bidsmetadata[bidsk] = v
                if len(bidsmetadata) > 0:
                    basename, _ = splitext(bidspath)
                    sidecarpath = bidspath.parent / f"{basename}.json"
                    with open(sidecarpath, "w") as f:
                        json.dump(bidsmetadata, f, indent=4)
