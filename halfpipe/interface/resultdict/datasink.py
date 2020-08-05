# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op
from pathlib import Path
import logging
from shutil import copyfile
from inflection import camelize
import hashlib
import json
import re

from nipype.interfaces.base import traits, TraitedSpec, SimpleInterface

from ...io import DictListFile
from ...model import ResultdictSchema, entities
from ...utils import splitext, findpaths, first, formatlikebids
from ...resource import get as getresource


def _make_path(type, tags, suffix, **kwargs):
    path = Path()

    assert type in ["report", "image"]

    for entity in ["sub", "ses"]:
        tagval = tags.get(entity)
        if tagval is not None:
            path = path.joinpath(f"{entity}-{tagval}")

    if type == "func":
        path = path.joinpath(f"func")

    if type == "report":
        path = path.joinpath(f"figures")

    filename = f"{suffix}.nii.gz"
    for tagname, tagval in reversed(kwargs.items()):  # reverse because we are prepending
        if tagval is not None:
            tagval = formatlikebids(tagval)
            filename = f"{tagname}-{tagval}_{filename}"
    for entity in entities:  # is already reversed
        tagval = tags.get(entity)
        if tagval is not None:
            filename = f"{entity}-{tagval}_{filename}"

    return path


def _copy_file(inpath, outpath):
    outpath.parent.mkdir(exist_ok=True, parents=True)
    if outpath.exists():
        if os.stat(inpath).st_mtime > os.stat(outpath).st_mtime:
            logging.getLogger("halfpipe").debug(f'Not overwriting file "{outpath}"')
            return
        logging.getLogger("halfpipe").info(f'Overwriting file "{outpath}"')
    copyfile(inpath, outpath)


def _find_sources(inpath):
    hash = None
    inputpaths = None
    for parent in Path(inpath).parents:
        hashfile = first(parent.glob("_0x*.json"))
        if hashfile is not None:
            match = re.match(r"_0x(?P<hash>[0-9a-f]{32})\.json", hashfile.name)
            if match is not None:
                hash = match.group("hash")
            with open(hashfile, "r") as fp:
                inputpaths = findpaths(json.load(fp))
                break
    return inputpaths, hash


class ResultdictDatasinkInputSpec(TraitedSpec):
    base_directory = traits.Directory(
        desc="Path to the base directory for storing data.", mandatory=True
    )
    indicts = traits.List(traits.Dict(traits.Str(), traits.Any()))


class ResultdictDatasink(SimpleInterface):
    input_spec = ResultdictDatasinkInputSpec
    output_spec = TraitedSpec

    always_run = True

    def _run_interface(self, runtime):
        base_directory = self.inputs.base_directory

        resultdict_schema = ResultdictSchema()

        base_directory = Path(self.base_directory)
        reports_directory = base_directory / "reports"

        indexhtml_path = reports_directory / "index.html"
        _copy_file(getresource("index.html"), indexhtml_path)

        valdicts = []
        imgdicts = []
        preprocdicts = []

        for indict in self.inputs.indicts:
            resultdict = resultdict_schema.dump(indict)

            tags = resultdict["tags"]
            metadata = resultdict["metadata"]
            images = resultdict["images"]
            reports = resultdict["reports"]
            vals = resultdict["vals"]

            metadata = {camelize(k): v for k, v in metadata.items()}

            # images

            for key, inpath in images.items():
                outpath = None
                if key in ["effect", "variance", "z", "dof"]:  # apply rule
                    outpath = base_directory / _make_path("image", tags, "statmap", stat=key)
                else:
                    outpath = base_directory / _make_path("image", tags, key)
                _copy_file(inpath, outpath)

                stem, _ = splitext(outpath)
                with open(f"{stem}.json", "w") as fp:
                    fp.write(json.dumps(metadata, sort_keys=True, indent=4))

                if key == "bold":
                    outdict = dict(**tags)
                    outdict.update({"status": "done"})
                    preprocdicts.append(outdict)

            # reports

            for key, inpath in reports.items():
                outpath = Path(self.base_directory)
                outpath = outpath.joinpath(_make_path("report", tags, key))
                _copy_file(inpath, outpath)

                hash = None
                sources = metadata.get("sources")

                if sources is None:
                    sources, hash = _find_sources(inpath)

                if hash is None:
                    md5 = hashlib.md5()
                    with open(inpath, "rb") as fp:
                        md5.update(fp.read())
                    hash = md5.hexdigest()

                outdict = dict(**tags)

                path = str(op.relpath(outpath, start=reports_directory))
                outdict.update({"desc": key, "path": path, "hash": hash})

                if sources is not None:
                    outdict["sourcefiles"] = []
                    for source in sources:
                        source = Path(source)
                        if base_directory in source.parents:
                            source = op.relpath(source, start=reports_directory)
                        outdict["sourcefiles"].append(str(source))

                imgdicts.append(outdict)

            # vals

            if len(vals) > 0:
                outdict = dict(**tags)
                outdict.update(vals)
                valdicts.append(outdict)

        # dictlistfile updates

        if len(valdicts) > 0:
            valspath = reports_directory / "reportvals.js"
            with DictListFile.cached(valspath) as valsfile:
                for valdict in valdicts:
                    valsfile.put(valdict)
                valsfile.to_table()

        if len(imgdicts) > 0:
            imgspath = reports_directory / "reportimgs.js"
            imgsfile = DictListFile.cached(imgspath)
            with imgsfile:
                for imgdict in imgdicts:
                    imgsfile.put(imgdict)

        if len(preprocdicts) > 0:
            preprocpath = reports_directory / "reportpreproc.js"
            with DictListFile.cached(preprocpath) as preprocfile:
                for preprocdict in preprocdicts:
                    preprocfile.put(preprocdict)
                preprocfile.to_table()

        return runtime
