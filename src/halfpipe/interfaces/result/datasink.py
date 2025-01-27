# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import hashlib
import json
import re
from os import path as op
from pathlib import Path

from nipype.interfaces.base import SimpleInterface, TraitedSpec, traits

from ...logging import logger
from ...model.tags import FuncTagsSchema
from ...resource import get as getresource
from ...result.bids.base import make_bids_path
from ...result.bids.images import save_images
from ...result.variables import Continuous
from ...utils.path import copy_if_newer, find_paths
from ...utils.table import SynchronizedTable


def _find_sources(inpath, metadata) -> tuple[list[str] | None, str | None]:
    file_hash = None

    sources = metadata.get("sources")
    if not isinstance(sources, list):
        sources = list()

    try:
        for parent in Path(inpath).parents:
            nipype_hash_file = None

            nipype_hash_files = list(parent.glob("_0x*.json"))
            if len(nipype_hash_files) > 0:
                nipype_hash_file = nipype_hash_files[0]

            if isinstance(nipype_hash_file, (str, Path)):
                nipype_hash_file = Path(nipype_hash_file)

                match = re.match(r"_0x(?P<hash>[0-9a-f]{32})\.json", nipype_hash_file.name)
                if match is not None:
                    file_hash = match.group("hash")

                with open(nipype_hash_file, "r") as file_handle:
                    nipype_hash_obj = json.load(file_handle)
                    sources.extend(find_paths(nipype_hash_obj))

                    break

    except Exception as e:
        logger.warning(f'Could not get sources for "{inpath}"', exc_info=e)

    return sources, file_hash


def _file_hash(path) -> str:
    md5 = hashlib.md5()
    with open(path, "rb") as fp:
        md5.update(fp.read())
    return md5.hexdigest()


def datasink_reports(indicts, reports_directory):
    index_html_download_path = Path(getresource("index.html"))
    index_html_target_path = reports_directory / "index.html"
    copy_if_newer(index_html_download_path, index_html_target_path)

    imgs_file_path = reports_directory / "reportimgs.js"

    with SynchronizedTable(imgs_file_path) as imgs_file:
        for indict in indicts:
            tags = indict.get("tags", dict())
            metadata = indict.get("metadata", dict())
            reports = indict.get("reports", dict())

            for key, inpath in reports.items():
                outpath = reports_directory / make_bids_path(inpath, "report", tags, key)
                copy_if_newer(inpath, outpath)

                file_hash = None
                sources, file_hash = _find_sources(inpath, metadata)

                if file_hash is None:
                    file_hash = _file_hash(inpath)

                outdict = dict(**tags)

                path = str(op.relpath(outpath, start=reports_directory))
                outdict.update({"desc": key, "path": path, "hash": file_hash})

                if sources is not None:
                    outdict["sourcefiles"] = []
                    for source in sources:
                        if reports_directory.parent in Path(source).parents:
                            source = op.relpath(source, start=reports_directory)
                        source_str = str(source)
                        if source_str not in outdict["sourcefiles"]:
                            outdict["sourcefiles"].append(source_str)

                imgs_file.put(outdict)


def datasink_vals(indicts, reports_directory):
    vals_file_path = reports_directory / "reportvals.js"

    with SynchronizedTable(vals_file_path) as vals_file:
        for indict in indicts:
            tags = indict.get("tags", dict())
            vals = indict.get("vals", dict())

            if len(vals) > 0 and "sub" in tags:  # only for first level
                outdict = FuncTagsSchema().dump(tags)
                assert isinstance(outdict, dict)

                for key, value in vals.items():
                    if key in frozenset(["sdc_method", "fallback_registration"]):
                        continue

                    if isinstance(value, (int, float)):
                        outdict[key] = value
                        continue

                    continuous = Continuous.load(value)
                    if continuous is not None:
                        outdict[key] = continuous.mean
                        continue

                    logger.warning(f'Omitting invalid key-value pair "{key}={value}" from reportvals.json')

                outdict.update(vals)

                vals_file.put(outdict)

        vals_file.to_table()


def datasink_preproc(indicts, reports_directory):
    preproc_file_path = reports_directory / "reportpreproc.js"

    with SynchronizedTable(preproc_file_path) as preproc_file:
        for indict in indicts:
            tags = indict.get("tags", dict())
            images = indict.get("images", dict())

            if len(images) > 0 and "sub" in tags:  # only for first level
                outdict = FuncTagsSchema().dump(tags)
                assert isinstance(outdict, dict)

                outdict["status"] = "done"

                preproc_file.put(outdict)


class ResultdictDatasinkInputSpec(TraitedSpec):
    base_directory = traits.Directory(desc="Path to the base directory for storing data.", mandatory=True)
    indicts = traits.List(traits.Dict(traits.Str(), traits.Any()))


class ResultdictDatasink(SimpleInterface):
    input_spec = ResultdictDatasinkInputSpec
    output_spec = TraitedSpec

    always_run: bool = True

    def _run_interface(self, runtime):
        indicts = self.inputs.indicts

        base_directory = Path(self.inputs.base_directory)

        reports_directory = base_directory / "reports"
        datasink_reports(indicts, reports_directory)
        datasink_vals(indicts, reports_directory)
        datasink_preproc(indicts, reports_directory)

        save_images(indicts, base_directory)

        return runtime
