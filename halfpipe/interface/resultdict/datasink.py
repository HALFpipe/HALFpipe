# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op
from pathlib import Path
from shutil import copyfile
import hashlib
import json
import re

from inflection import camelize

from nipype.interfaces.base import traits, TraitedSpec, SimpleInterface
# from niworkflows.viz.utils import compose_view, extract_svg
# from nilearn.plotting import plot_glass_brain

from ...io import DictListFile
from ...model import FuncTagsSchema, ResultdictSchema, entities, resultdict_entities
from ...utils import splitext, findpaths, first, formatlikebids, logger
from ...resource import get as getresource


def _make_plot(tags, key, sourcefile):
    if key == "z":
        pass
    elif key == "matrix":
        pass


def _make_path(sourcefile, type, tags, suffix, **kwargs):
    path = Path()

    assert type in ["report", "image"]

    for entity in ["sub", "ses"]:
        tagval = tags.get(entity)
        if tagval is not None:
            tagval = formatlikebids(tagval)
            path = path.joinpath(f"{entity}-{tagval}")

    if type == "image":
        path = path.joinpath("func")

    if type == "report":
        path = path.joinpath("figures")

    _, ext = splitext(sourcefile)
    filename = f"{suffix}{ext}"  # keep original extension
    kwtags = list(kwargs.items())
    for tagname, tagval in reversed(kwtags):  # reverse because we are prepending
        if tagval is not None:
            tagval = formatlikebids(tagval)
            filename = f"{tagname}-{tagval}_{filename}"
    for entity in entities:  # is already reversed
        tagval = tags.get(entity)
        if tagval is not None:
            tagval = formatlikebids(tagval)
            filename = f"{entity}-{tagval}_{filename}"

    return path / filename


def _copy_file(inpath, outpath):
    outpath.parent.mkdir(exist_ok=True, parents=True)
    if outpath.exists():
        if os.stat(inpath).st_mtime <= os.stat(outpath).st_mtime:
            logger.info(f'Not overwriting file "{outpath}"')
            return False
        logger.info(f'Overwriting file "{outpath}"')
    else:
        logger.info(f'Creating file "{outpath}"')
    copyfile(inpath, outpath)
    return True


def _find_sources(inpath):
    file_hash = None
    inputpaths = None
    for parent in Path(inpath).parents:

        hashfile = first(parent.glob("_0x*.json"))

        if isinstance(hashfile, Path):

            match = re.match(r"_0x(?P<hash>[0-9a-f]{32})\.json", hashfile.name)
            if match is not None:
                file_hash = match.group("hash")

            with open(hashfile, "r") as fp:
                inputpaths = findpaths(json.load(fp))
                break

    return inputpaths, file_hash


def _format_metadata_value(obj):
    if not isinstance(obj, dict):
        return obj
    return {
        _format_metadata_key(k): _format_metadata_value(v)
        for k, v in obj.items()
    }


def _format_metadata_key(key):  # camelize
    if key == "ica_aroma":
        return "ICAAROMA"
    if key == "fwhm":
        return "FWHM"
    if key == "hp_width":
        return "HighPassWidth"
    if key == "lp_width":
        return "LowPassWidth"
    return camelize(key)


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
        base_directory = Path(self.inputs.base_directory)

        resultdict_schema = ResultdictSchema()

        grouplevel_directory = base_directory / "grouplevel"
        derivatives_directory = base_directory / "derivatives" / "halfpipe"
        reports_directory = base_directory / "reports"

        indexhtml_path = reports_directory / "index.html"
        _copy_file(getresource("index.html"), indexhtml_path)

        valdicts = []
        imgdicts = []
        preprocdicts = []

        for indict in self.inputs.indicts:
            resultdict = resultdict_schema.dump(indict)

            assert isinstance(resultdict, dict)

            tags = resultdict["tags"]
            metadata = resultdict["metadata"]
            images = resultdict["images"]
            reports = resultdict["reports"]
            vals = resultdict["vals"]

            metadata = _format_metadata_value(metadata)

            # images

            for key, inpath in images.items():
                outpath = derivatives_directory
                if "sub" not in tags:
                    outpath = grouplevel_directory
                if key in ["effect", "variance", "z", "dof"]:  # apply rule
                    outpath = outpath / _make_path(inpath, "image", tags, "statmap", stat=key)
                else:
                    outpath = outpath / _make_path(inpath, "image", tags, key)
                was_updated = _copy_file(inpath, outpath)

                if was_updated:
                    _make_plot(tags, key, outpath)

                if key in ["effect", "reho", "falff", "alff", "bold", "timeseries"]:
                    stem, extension = splitext(outpath)
                    if extension in [".nii", ".nii.gz", ".tsv"]:
                        with open(outpath.parent / f"{stem}.json", "w") as fp:
                            fp.write(json.dumps(metadata, sort_keys=True, indent=4))

                # any file means that preprocessing finished
                outdict = dict(**tags)
                for k in resultdict_entities:
                    if k in outdict:
                        del outdict[k]
                outdict.update({"status": "done"})
                preprocdicts.append(outdict)

            # reports

            for key, inpath in reports.items():
                outpath = reports_directory / _make_path(inpath, "report", tags, key)
                _copy_file(inpath, outpath)

                file_hash = None
                sources = metadata.get("sources")

                if sources is None:
                    sources = list()

                try:
                    found_sources, file_hash = _find_sources(inpath)

                    if isinstance(found_sources, list):
                        sources.extend(found_sources)
                except Exception as e:
                    logger.warning(f'Could not get sources for "{inpath}"', exc_info=e)

                if file_hash is None:
                    md5 = hashlib.md5()
                    with open(inpath, "rb") as fp:
                        md5.update(fp.read())
                    file_hash = md5.hexdigest()

                outdict = dict(**tags)

                path = str(op.relpath(outpath, start=reports_directory))
                outdict.update({"desc": key, "path": path, "hash": file_hash})

                if sources is not None:
                    outdict["sourcefiles"] = []
                    for source in sources:
                        source = Path(source)
                        if base_directory in source.parents:
                            source = op.relpath(source, start=reports_directory)
                        source_str = str(source)
                        if source_str not in outdict["sourcefiles"]:
                            outdict["sourcefiles"].append(source_str)

                imgdicts.append(outdict)

            # vals

            if len(vals) > 0 and "model" not in tags:  # only for first level
                outdict = FuncTagsSchema().dump(tags)

                assert isinstance(outdict, dict)

                outdict.update(vals)
                valdicts.append(outdict)

        # dictlistfile updates

        if len(valdicts) > 0:
            valspath = reports_directory / "reportvals.js"
            valsfile = DictListFile.cached(valspath)
            with valsfile:
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
            preprocfile = DictListFile.cached(preprocpath)
            with preprocfile:
                for preprocdict in preprocdicts:
                    preprocfile.put(preprocdict)
                preprocfile.to_table()

        return runtime
