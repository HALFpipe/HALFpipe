# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
import logging
from shutil import copyfile
import json
import re
import hashlib
from os import path as op

from .dictlistfile import DictListFile
from ..spec import bold_entities
from ..utils import splitext, first, findpaths


def make_path(entitytupls):
    path = Path()
    for entity, value in reversed(entitytupls):
        path = path.joinpath(f"{entity}_{value}")
    return path


class ResultHook:
    def __init__(self, base_directory):
        self.base_directory = base_directory

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass

    def run(self, resultdict):
        entitytupls = [(k, resultdict[k]) for k in bold_entities if k in resultdict]
        if len(entitytupls) == 0:
            return

        valuedict = {k: v for k, v in resultdict.items() if k in self.keys}
        if len(valuedict) == 0:
            return

        self._run_hook(entitytupls, valuedict)

    def _copy_file(self, in_filepath, out_filepath):
        if out_filepath.exists():
            logging.getLogger("pipeline").info(f'Overwriting file "{out_filepath}"')
        copyfile(in_filepath, out_filepath)

    def _run_hook(self, entitytupls, valuedict):
        out_directory = Path(self.base_directory) / self.subdirectory / make_path(entitytupls)
        out_directory.mkdir(parents=True, exist_ok=True)

        for key, value in valuedict.items():
            if isinstance(value, str) and Path(value).exists():
                _, ext = splitext(value)
                out_filepath = out_directory / f"{key}{ext}"
                self._copy_file(value, out_filepath)


class PreprocessedImgCopyOutResultHook(ResultHook):
    subdirectory = "subjectlevel"
    keys = ["preproc", "confounds", "mask_file"]

    def __init__(self, base_directory):
        super(PreprocessedImgCopyOutResultHook, self).__init__(base_directory)

        dictlistfilename = Path(self.base_directory) / "reports" / "reportpreproc.js"
        self.dictlistfile = DictListFile(dictlistfilename, "report('", "');")

    def __enter__(self):
        self.dictlistfile.__enter__()

    def __exit__(self, *args):
        self.dictlistfile.to_table()
        self.dictlistfile.__exit__(*args)

    def init_dictlistfile(self, dictlist):
        with self:
            for statusdict in dictlist:
                statusdict.update({"status": "missing"})
                self.dictlistfile.put(statusdict)

    def _run_hook(self, entitytupls, valuedict):
        if "preproc" not in valuedict:
            return

        super(PreprocessedImgCopyOutResultHook, self)._run_hook(entitytupls, valuedict)

        statusdict = dict(entitytupls)
        statusdict.update({"status": "done"})
        self.dictlistfile.put(statusdict)


class ReportValsResultHook(ResultHook):
    subdirectory = "reports"
    keys = ["mean_fd", "fd_gt_0_5", "aroma_noise_frac", "mean_gm_tsnr", "fmap_type"]

    def __init__(self, base_directory):
        super(ReportValsResultHook, self).__init__(base_directory)

        dictlistfilename = Path(self.base_directory) / self.subdirectory / "reportvals.js"
        self.dictlistfile = DictListFile(dictlistfilename, "report('", "');")

    def __enter__(self):
        self.dictlistfile.__enter__()

    def __exit__(self, *args):
        self.dictlistfile.to_table()
        self.dictlistfile.__exit__(*args)

    def _run_hook(self, entitytupls, valuedict):
        valuedict.update(entitytupls)
        self.dictlistfile.put(valuedict)


class ReportImgResultHook(ResultHook):
    subdirectory = "reports"
    keys = ["desc", "report"]

    def __init__(self, base_directory):
        super(ReportImgResultHook, self).__init__(base_directory)

        dictlistfilename = Path(self.base_directory) / self.subdirectory / "reportimgs.js"
        self.dictlistfile = DictListFile(dictlistfilename, "report('", "');")

    def __enter__(self):
        self.dictlistfile.__enter__()

    def __exit__(self, *args):
        self.dictlistfile.__exit__(*args)

    def _run_hook(self, entitytupls, valuedict):
        if "report" not in valuedict:
            return
        if "desc" not in valuedict:
            return

        base_directory = Path(self.base_directory)
        reports_directory = base_directory / self.subdirectory
        out_directory = reports_directory / make_path(entitytupls)
        out_directory.mkdir(parents=True, exist_ok=True)

        desc = valuedict["desc"]
        report_file = valuedict["report"]

        if not Path(report_file).exists():
            return

        _, ext = splitext(report_file)
        out_filepath = out_directory / f"{desc}{ext}"
        self._copy_file(report_file, out_filepath)

        hash = None
        inputpaths = None
        for parent in Path(report_file).parents:
            hashfile = first(parent.glob("_0x*.json"))
            if hashfile is not None:
                match = re.match(r"_0x(?P<hash>[0-9a-f]{32})\.json", hashfile.name)
                if match is not None:
                    hash = match.group("hash")
                with open(hashfile, "r") as fp:
                    inputpaths = findpaths(json.load(fp))
                    break

        if hash is None:
            md5 = hashlib.md5()
            with open(report_file, "rb") as fp:
                md5.update(fp.read())
            hash = md5.hexdigest()

        outdict = dict(entitytupls)

        path = str(op.relpath(out_filepath, start=reports_directory))
        outdict.update({"desc": desc, "path": path, "hash": hash})

        if inputpaths is not None:
            outdict["sourcefiles"] = []
            for inputpath in inputpaths:
                inputpath = Path(inputpath)
                if base_directory in inputpath.parents:
                    inputpath = op.relpath(inputpath, start=reports_directory)
                outdict["sourcefiles"].append(str(inputpath))

        self.dictlistfile.put(outdict)


class SubjectLevelFeatureCopyOutResultHook(ResultHook):
    subdirectory = "subjectlevel"
    keys = [
        "firstlevelanalysisname",
        "firstlevelfeaturename",
        "stat",
        "cope",
        "varcope",
        "zstat",
        "dof_file",
        "mask_file",
        "time_series",
        "covariance",
        "correlation",
        "partial_correlation",
    ]

    def _run_hook(self, entitytupls, valuedict):
        if "firstlevelanalysisname" not in valuedict:
            return
        if "firstlevelfeaturename" not in valuedict:
            return
        if not any(k == "subject" for k, v in entitytupls):
            return

        out_directory = Path(self.base_directory) / self.subdirectory / make_path(entitytupls)

        analysis_name = valuedict["firstlevelanalysisname"]
        feature_name = valuedict["firstlevelfeaturename"]
        out_directory = out_directory / f"analysis_{analysis_name}" / feature_name

        out_directory.mkdir(parents=True, exist_ok=True)

        for key, value in valuedict.items():
            if isinstance(value, str) and Path(value).exists():
                _, ext = splitext(value)
                out_filepath = out_directory / f"{key}{ext}"
                self._copy_file(value, out_filepath)


class GroupLevelFeatureCopyOutResultHook(ResultHook):
    subdirectory = "grouplevel"
    keys = [
        "analysisname",
        "contrastname",
        "firstlevelanalysisname",
        "firstlevelfeaturename",
        "cope",
        "varcope",
        "zstat",
        "dof_file",
        "mask_file",
    ]

    def _run_hook(self, entitytupls, valuedict):
        if "analysisname" not in valuedict:
            return
        if "contrastname" not in valuedict:
            return
        if "firstlevelanalysisname" not in valuedict:
            return
        if "firstlevelfeaturename" not in valuedict:
            return
        if any(k == "subject" for k, v in entitytupls):
            return

        out_directory = Path(self.base_directory) / self.subdirectory / make_path(entitytupls)

        analysis_name = valuedict["analysisname"]
        contrast_name = valuedict["contrastname"]
        out_directory = out_directory / f"analysis_{analysis_name}" / contrast_name

        analysis_name = valuedict["firstlevelanalysisname"]
        feature_name = valuedict["firstlevelfeaturename"]
        out_directory = out_directory / f"firstlevelanalysis_{analysis_name}" / feature_name

        out_directory.mkdir(parents=True, exist_ok=True)

        for key, value in valuedict.items():
            if isinstance(value, str) and Path(value).exists():
                _, ext = splitext(value)
                out_filepath = out_directory / f"{key}{ext}"
                self._copy_file(value, out_filepath)


def get_resulthooks(base_directory):
    return [
        PreprocessedImgCopyOutResultHook(base_directory),
        ReportValsResultHook(base_directory),
        ReportImgResultHook(base_directory),
        SubjectLevelFeatureCopyOutResultHook(base_directory),
        GroupLevelFeatureCopyOutResultHook(base_directory),
    ]
