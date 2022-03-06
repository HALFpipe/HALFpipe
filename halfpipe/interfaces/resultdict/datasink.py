# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import hashlib
import json
import os
import re
from os import path as op
from pathlib import Path
from shutil import copyfile

from inflection import camelize
from nipype.interfaces.base import SimpleInterface, TraitedSpec, traits

from ...model import FuncTagsSchema, entities
from ...model.tags.resultdict import first_level_entities
from ...resource import get as getresource
from ...stats.algorithms import algorithms
from ...utils import logger
from ...utils.format import format_like_bids
from ...utils.json import TypeAwareJSONEncoder
from ...utils.path import find_paths, split_ext
from ...utils.table import SynchronizedTable
from .base import Continuous

# from niworkflows.viz.utils import compose_view, extract_svg
# from nilearn.plotting import plot_glass_brain


def _make_plot(tags, key, sourcefile, metadata):
    _, _, _ = tags, sourcefile, metadata
    if key == "z":
        pass
    elif key == "matrix":
        pass


def _join_tags(tags: dict[str, str], entities: list[str] | None = None) -> str | None:
    joined = None

    if entities is None:
        entities = list(tags.keys())

    for entity in entities:
        if entity not in tags:
            continue
        value = tags[entity]
        value = format_like_bids(value)

        if joined is None:
            joined = f"{entity}-{value}"
        else:
            joined = f"{joined}_{entity}-{value}"

    return joined


def _make_path(source_file, source_type, tags, suffix, **kwargs):
    path = Path()

    for entity in ["sub", "ses"]:
        folder_name = _join_tags(tags, [entity])
        if folder_name is not None:
            path = path.joinpath(folder_name)

    path = path.joinpath(dict(image="func", report="figures")[source_type])

    if "feature" in tags:  # make subfolders for all feature outputs
        folder_entities = ["task"]
        if "sub" not in tags:
            folder_entities.extend(first_level_entities)

        folder_name = _join_tags(tags, folder_entities)
        if folder_name is not None:
            path = path.joinpath(folder_name)

    if "sub" not in tags:
        folder_name = _join_tags(tags, ["model"])
        assert folder_name is not None
        path = path.joinpath(folder_name)

    _, ext = split_ext(source_file)
    filename = f"{suffix}{ext}"  # keep original extension

    kwargs_str = _join_tags(kwargs)
    if kwargs_str is not None:
        filename = f"{kwargs_str}_{filename}"

    tags_str = _join_tags(tags, list(reversed(entities)))
    if tags_str is not None:
        filename = f"{tags_str}_{filename}"

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

                match = re.match(
                    r"_0x(?P<hash>[0-9a-f]{32})\.json", nipype_hash_file.name
                )
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
    indexhtml_path = reports_directory / "index.html"
    _copy_file(getresource("index.html"), indexhtml_path)

    imgs_file_path = reports_directory / "reportimgs.js"

    with SynchronizedTable(imgs_file_path) as imgs_file:
        for indict in indicts:
            tags = indict.get("tags", dict())
            metadata = indict.get("metadata", dict())
            reports = indict.get("reports", dict())

            for key, inpath in reports.items():
                outpath = reports_directory / _make_path(inpath, "report", tags, key)
                _copy_file(inpath, outpath)

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
                        source = Path(source)
                        if reports_directory.parent in source.parents:
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

                    logger.warning(
                        f'Omitting invalid key-value pair "{key}={value}"'
                        " from reportvals.json"
                    )

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

        preproc_file.to_table()


def _format_sidecar_value(obj):
    if not isinstance(obj, dict):
        return obj
    return {_format_sidecar_key(k): _format_sidecar_value(v) for k, v in obj.items()}


def _format_sidecar_key(key):  # camelize
    predefined = dict(
        ica_aroma="ICAAROMA",
        fwhm="FWHM",
        hp_width="HighPassWidth",
        lp_width="LowPassWidth",
        fd_perc="FDPerc",
        fd_mean="FDMean",
        mean_gm_tsnr="MeanGMTSNR",
        mean_seed_tsnr="MeanSeedTSNR",
        mean_component_tsnr="MeanComponentTSNR",
        mean_atlas_tsnr="MeanAtlasTSNR",
    )
    if key in predefined:
        return predefined[key]
    return camelize(key)


def datasink_images(indicts, base_directory):
    derivatives_directory = base_directory / "derivatives" / "halfpipe"
    grouplevel_directory = base_directory / "grouplevel"

    for indict in indicts:
        tags = indict.get("tags", dict())
        metadata = indict.get("metadata", dict())
        vals = indict.get("vals", dict())
        images = indict.get("images", dict())

        # images

        for key, inpath in images.items():
            outpath = derivatives_directory

            if "sub" not in tags:
                outpath = grouplevel_directory

            if key in ["effect", "variance", "z", "t", "f", "dof"]:  # apply rule
                outpath = outpath / _make_path(
                    inpath, "image", tags, "statmap", stat=key
                )

            elif key in algorithms["heterogeneity"].model_outputs:
                key = re.sub(r"^het", "", key)
                outpath = outpath / _make_path(
                    inpath,
                    "image",
                    tags,
                    "statmap",
                    algorithm="heterogeneity",
                    stat=key,
                )

            elif key in algorithms["mcartest"].model_outputs:
                key = re.sub(r"^mcar", "", key)
                outpath = outpath / _make_path(
                    inpath, "image", tags, "statmap", algorithm="mcar", stat=key
                )

            else:
                outpath = outpath / _make_path(inpath, "image", tags, key)

            was_updated = _copy_file(inpath, outpath)

            if was_updated:
                _make_plot(tags, key, outpath, metadata)

            if key in ["effect", "reho", "falff", "alff", "bold", "timeseries"]:
                stem, extension = split_ext(outpath)
                if extension in [".nii", ".nii.gz", ".tsv"]:  # add sidecar

                    sidecar = metadata.copy()
                    sidecar.update(vals)
                    sidecar = _format_sidecar_value(sidecar)

                    sidecar_json = json.dumps(
                        sidecar, cls=TypeAwareJSONEncoder, sort_keys=True, indent=4
                    )

                    sidecar_file_path = outpath.parent / f"{stem}.json"
                    with open(sidecar_file_path, "wt") as sidecar_file_handle:
                        sidecar_file_handle.write(sidecar_json)


class ResultdictDatasinkInputSpec(TraitedSpec):
    base_directory = traits.Directory(
        desc="Path to the base directory for storing data.", mandatory=True
    )
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

        datasink_images(indicts, base_directory)

        return runtime
