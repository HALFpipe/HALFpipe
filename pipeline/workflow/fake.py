# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

import gzip
import fasteners
import json
import pickle

from shutil import copy, copyfileobj
from pathlib import Path

import re
from pkg_resources import resource_filename as pkgr

from ..utils import (
    deepvalues,
    _ravel,
    _splitext
)
from ..fmriprepsettings import bids_dir

from nipype.interfaces.base import (
    isdefined,
    SimpleInterface
)
from fmriprep.interfaces import DerivativesDataSink
from bids.layout import Config
config = Config.load("bids")


class FakeBIDSFile:
    def __init__(self, path):
        self.path = path


class FakeBIDSLayout:

    def __init__(self,
                 bold_file, metadata):

        self.root = bids_dir

        self.bold_file = bold_file
        self.metadata = metadata

    def get(self, return_type="object", target=None, scope="all",
            regex_search=False, absolute_paths=None, drop_invalid_filters=True,
            **filters):
        return []

    def get_metadata(self, path):
        if path == self.bold_file:
            return self.metadata
        else:
            return dict()

    def parse_file_entities(self, filename,
                            include_unmatched=False):
        bf = FakeBIDSFile(filename)
        ent_vals = {}
        for ent in config.entities.values():
            match = ent.match_file(bf)
            if match is not None or include_unmatched:
                ent_vals[ent.name] = match
        return ent_vals

    def get_fieldmap(self, path, return_list=False):
        if return_list:  # fieldmaps are not supported
            return []
        return None


def _find(target, d):
    for k, v in d.items():
        if isinstance(v, str) and v == target:
            return k
        elif isinstance(v, dict):
            a = _find(target, v)
            if a is not None:
                return k + "/" + a
    return None


class FakeDerivativesDataSink(DerivativesDataSink):
    def __init__(self,
                 images, output_dir,
                 fmriprep_reportlets_dir, fmriprep_output_dir,
                 node_id, depends,
                 **inputs):
        super(FakeDerivativesDataSink, self).__init__(**inputs)

        self.images = images
        self.output_dir = output_dir
        self.fmriprep_reportlets_dir = fmriprep_reportlets_dir
        self.fmriprep_output_dir = fmriprep_output_dir
        self.node_id = node_id
        self.depends = depends

    def _run_interface(self, runtime):
        out_path = _find(self.inputs.source_file, self.images)

        if out_path is None:
            for k in self.images.keys():
                if k in self.inputs.in_file[0]:
                    out_path = k
            if "anat" in self.inputs.in_file[0]:
                out_path = out_path + "/" + "T1w"

        if out_path is None:
            out_path = ""

        _, ext = _splitext(self.inputs.in_file[0])
        compress = ext == ".nii"
        if compress:
            ext = ".nii.gz"

        base_directory = runtime.cwd
        if isdefined(self.inputs.base_directory):
            base_directory = op.abspath(self.inputs.base_directory)

        if base_directory == self.fmriprep_output_dir:
            # don"t copy file
            return runtime
        elif base_directory == self.fmriprep_reportlets_dir:
            # write to json
            work_dir = base_directory
            json_id = "%s.%s" % (self.node_id, self.inputs.suffix)
            json_id = re.sub(r"func_preproc_[^.]*", "func_preproc_wf", json_id)
            json_data = {"id": json_id}

            os.makedirs(op.join(work_dir, out_path), exist_ok=True)

            # discover source files
            sourceImages = []

            def extractSourceImages(finputs):
                with gzip.open(finputs, "r") as file:
                    inputs = pickle.load(file)
                    for valuelist in inputs.values():
                        if valuelist is not None and \
                                (isinstance(valuelist, list) or
                                 isinstance(valuelist, str)):
                            valuelist = _ravel(valuelist)
                            for value in valuelist:
                                if value is not None and \
                                        isinstance(value, str) and \
                                        value.endswith(".nii.gz"):
                                    sourceImages.append(value)

            for fname in self.inputs.in_file:
                finputs = op.join(op.dirname(fname), "_inputs.pklz")
                if op.isfile(finputs):
                    extractSourceImages(finputs)
                else:
                    finputs = op.join(
                        op.dirname(op.dirname(fname)), "_inputs.pklz")
                    if op.isfile(finputs):
                        extractSourceImages(finputs)

            # output relative path only for derivatives, not for input images
            dataImages = set(deepvalues(self.images))
            sourceImages = [
                op.relpath(s, start=work_dir)
                if s not in dataImages else s for s in sourceImages]

            # output path for images
            touch_fname = op.join(out_path, json_data["id"] + ext)
            touch_path = op.join(work_dir, touch_fname)

            if not op.isfile(touch_path):
                for i, fname in enumerate(self.inputs.in_file):
                    copy(fname, touch_path)

                json_data["fname"] = op.join(touch_fname)
                json_data["sources"] = sourceImages
                with fasteners.InterProcessLock(
                        op.join(work_dir, "qualitycheck.lock")):
                    json_file = op.join(work_dir, "qualitycheck.js")
                    with open(json_file, "ab+") as f:
                        f.seek(0, 2)

                        closingCharacters = "]'))"

                        if f.tell() == 0:
                            f.write("qualitycheck(JSON.parse('".encode())
                            f.write(json.dumps([json_data]).encode())
                            # skip json list bracket
                            f.write(closingCharacters[1:].encode())
                        else:
                            f.seek(-len(closingCharacters), 2)
                            f.truncate()
                            f.write(",".encode())
                            f.write(json.dumps(json_data).encode())
                            f.write(closingCharacters.encode())
                Path(touch_path).touch()

            html_path = op.join(work_dir, "index.html")
            if not op.isfile(html_path):
                copy(pkgr("pipeline", "index.html"), html_path)
        else:
            # copy file to out_path
            out_path = op.join(base_directory, out_path)

            os.makedirs(out_path, exist_ok=True)

            formatstr = "{suffix}{ext}"
            if len(self.inputs.in_file) > 1 and \
                    not isdefined(self.inputs.extra_values):
                formatstr = "{suffix}{i:04d}{ext}"

            for i, fname in enumerate(self.inputs.in_file):
                out_file = formatstr.format(
                    suffix=self.inputs.suffix,
                    i=i,
                    ext=ext
                )

                if isdefined(self.inputs.extra_values):
                    out_file = out_file.format(
                        extra_value=self.inputs.extra_values[i]
                    )

                out_file = op.join(out_path, out_file)

                self._results["out_file"].append(out_file)

                if compress:
                    with open(fname, "rb") as f_in:
                        with gzip.open(out_file, "wb") as f_out:
                            copyfileobj(f_in, f_out)
                else:
                    copy(fname, out_file)

        return runtime


class FakeReadSidecarJSON(SimpleInterface):
    def _run_interface(self, runtime):
        pass
