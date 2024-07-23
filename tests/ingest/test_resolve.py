# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from datetime import datetime
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest
import requests
from halfpipe.ingest.resolve import ResolvedSpec
from halfpipe.model.file.base import File
from halfpipe.model.spec import Spec


@pytest.mark.parametrize(
    ("openneuro_id"),
    (
        ("ds004109"),
        ("ds004187"),
        ("ds004161"),
    ),
)
def test_resolve_bids(tmp_path: Path, openneuro_id: str):
    # Get file names with GraphQL request
    query_example = f"""query{{
    snapshot(datasetId: "{openneuro_id}", tag: "1.0.0"){{
        files{{
            id
            key
            filename
            size
            directory
            annexed
            }}
        }}
    }}"""

    gql_url = "https://openneuro.org/crn/graphql"

    r = requests.post(gql_url, json={"query": query_example})
    if not r.status_code == 200:
        raise RuntimeError("Could not fetch file listing")

    json_file = json.loads(r.text)

    def recursive_walk_wpath(neuro_dict, file_list: list[str] | None = None, build_path=None):
        if file_list is None:
            file_list = list()

        base_list = neuro_dict["data"]["snapshot"]["files"]  # returns list of all files
        if build_path is None:
            build_path = []
        for i, val in enumerate(base_list):
            if not val["directory"]:
                p = "/".join(str(x) for x in build_path)
                x = p + "/" + val["filename"]
                if x.startswith("/"):
                    x = x[1:]
                file_list.append(x.strip())
                continue
            cur_id = val["id"]
            cur_fname = val["filename"]
            if i == 0 and len(build_path) == 2:  # delete current sub-0* folder when going to next sub-0*
                del build_path[0]
            elif i > 0 and build_path:  # delete subfolders of sub-0* folders when going to next subfolder
                del build_path[-1]
            build_path.append(cur_fname)
            query = f"""query{{
                snapshot(datasetId: "{openneuro_id}", tag: "1.0.0"){{
                    files(tree: "{cur_id}"){{
                        id
                        key
                        filename
                        directory
                        }}
                    }}
                }}"""
            r = requests.post(gql_url, json={"query": query})
            json_dict = json.loads(r.text)
            recursive_walk_wpath(json_dict, build_path=build_path)
        return file_list

    file_list: list[str] = recursive_walk_wpath(neuro_dict=json_file)

    for line in file_list:
        if not isinstance(line, str):
            continue
        if line.endswith(("MP2RAGE.nii.gz", "UNIT1.nii.gz")):
            continue
        if "T1map" in line:
            continue
        path = tmp_path / line.strip()

        path.parent.mkdir(parents=True, exist_ok=True)
        if line.endswith(".json"):
            with open(path, "w") as file_handle:
                file_handle.write("{}")
        elif line.endswith(".nii.gz"):
            empty_image = nib.nifti1.Nifti1Image(np.zeros(0), np.eye(4))
            nib.loadsave.save(empty_image, path)
        path.touch()

    spec = Spec(datetime.now(), [])
    resolved_spec = ResolvedSpec(spec)

    file_obj = File(str(tmp_path), "bids")
    resolved_files = resolved_spec.resolve(file_obj)

    counter = 0
    for i in file_list:
        if i.startswith("derivatives") or "/dwi" in i or "T1map" in i or i.endswith(("MP2RAGE.nii.gz", "UNIT1.nii.gz")):
            continue
        if i.endswith(("events.tsv", ".nii.gz", ".nii")):
            counter += 1
    assert counter == len(resolved_files)
