# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from os.path import relpath
from shutil import rmtree
import json
from collections import OrderedDict

from inflection import camelize

from calamities.pattern.glob import _rlistdir
from ...model.file import FileSchema
from ...model.tags import entity_longnames, entities
from ...model.utils import get_nested_schema_field_names
from ...utils import formatlikebids, splitext
from ..metadata import canonicalize_direction_code

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
                bidstags[bidsentity] = formatlikebids(v)
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

        bidspaths = set()

        dataset_description_path = bidsdir / "dataset_description.json"
        bidspaths.add(dataset_description_path)

        dataset_description = {
            "Name": self.database.sha1,
            "BIDSVersion": bidsversion,
            "DatasetType": "raw",
        }

        with open(dataset_description_path, "w") as f:
            json.dump(dataset_description, f, indent=4)

        # image files
        for bidspath, filepath in self.filepaths_by_bidspaths.items():
            bidspath = Path(bidsdir) / bidspath
            bidspaths.add(bidspath)
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

        # sidecar files
        for bidspath, filepath in self.filepaths_by_bidspaths.items():
            schema = FileSchema
            while hasattr(schema, "type_field") and hasattr(schema, "type_schemas"):
                v = self.database.tagval(filepath, schema.type_field)
                schema = schema.type_schemas[v]
            instance = schema()

            bidsmetadata = OrderedDict()
            if "metadata" in instance.fields:
                metadata_keys = get_nested_schema_field_names(instance, "metadata")

                # manual conversion
                task = self.database.tagval(filepath, "task")
                if task is not None:
                    bidsmetadata["TaskName"] = task

                # automated
                for k in metadata_keys:
                    self.database.fillmetadata(k, [filepath])
                    v = self.database.metadata(filepath, k)
                    if v is not None:
                        # transform metadata
                        if k.endswith("direction"):
                            v = canonicalize_direction_code(v, filepath)
                        if k == "slice_timing_code":
                            if not self.database.fillmetadata("slice_timing", [filepath]):
                                continue
                            k = "slice_timing"
                            v = self.database.metadata(filepath, k)
                        bidsk = camelize(k)
                        # add to sidecar
                        bidsmetadata[bidsk] = v

            if self.database.tagval(filepath, "datatype") == "fmap":
                if self.database.tagval(filepath, "suffix") not in ["magnitude1", "magnitude2"]:
                    sub = self.database.tagval(filepath, "sub")
                    ses = self.database.tagval(filepath, "ses")
                    subject = self.tagval(bidspath, "subject")

                    subjectdir = f"sub-{subject}"

                    bidsmetadata["IntendedFor"] = list()

                    filters = dict(datatype="func", suffix="bold", sub=sub)
                    if ses is not None:
                        filters.update(dict(ses=ses))
                    afilepaths = self.database.associations(filepath, **filters)
                    if afilepaths is None:
                        continue  # only write if we can find a functional image

                    afilepaths = sorted(afilepaths)

                    for afilepath in afilepaths:
                        abidspath = self.tobids(afilepath)
                        if abidspath is not None:  # only include files in the BidsDatabase
                            bidsmetadata["IntendedFor"].append(relpath(abidspath, start=subjectdir))

                    if len(bidsmetadata["IntendedFor"]) == 0:
                        bidsmetadata = dict()
                        bidspaths.discard(filepath)

            if len(bidsmetadata) > 0:
                basename, _ = splitext(bidspath)
                sidecarpath = Path(bidsdir) / Path(bidspath).parent / f"{basename}.json"
                bidspaths.add(sidecarpath)
                jsonstr = json.dumps(bidsmetadata, indent=4, sort_keys=False)
                if sidecarpath.is_file():
                    with open(sidecarpath, "r") as f:
                        if jsonstr == f.read():
                            continue
                with open(sidecarpath, "w") as f:
                    f.write(jsonstr)

        # remove unnecessary files
        files_to_keep = set()
        for bidspath in bidspaths:
            relbidspath = relpath(bidspath, start=bidsdir)
            # use relative paths to limit parents to bidsdir
            files_to_keep.add(relbidspath)
            files_to_keep.update(map(str, Path(relbidspath).parents))

        for filepath in _rlistdir(bidsdir, False):
            relfilepath = relpath(filepath, start=bidsdir)
            if relfilepath not in files_to_keep:
                p = Path(filepath)
                if not p.is_dir():
                    p.unlink()
                else:
                    rmtree(p)
