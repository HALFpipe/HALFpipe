# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
from datetime import datetime
from pathlib import Path

import pytest
import requests

from ...model.file.base import File
from ...model.spec import Spec
from ..resolve import ResolvedSpec


@pytest.mark.parametrize(
    ("openneuroID"),
    (
        ("ds004109"),
        ("ds004187"),
        ("ds004161"),
    ),
)
def test__resolve_bids(tmp_path: Path, openneuroID: str):
    # Get file names with GraphQL request
    query_example = f"""query{{
    snapshot(datasetId: "{openneuroID}", tag: "1.0.0"){{
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
    # attempts = 0
    # while attempts < 3:
    #   r = requests.post(gql_url, json={"query": query_example})
    #  if not r.status_code == 200:
    #     time.sleep(0.3)
    #    attempts += 1
    #   continue
    # break

    r = requests.post(gql_url, json={"query": query_example})
    print(r.status_code)
    if not r.status_code == 200:
        raise RuntimeError("Could not fetch file listing")

    json_file = json.loads(r.text)

    def recursive_walk(neuro_dict, file_list: list = []):
        base_list = neuro_dict["data"]["snapshot"]["files"]  # returns list of all files
        for val in base_list:
            if not val["directory"]:
                file_list.append(val["filename"])
            cur_id = val["id"]
            query = f"""query{{
                snapshot(datasetId: "{openneuroID}", tag: "1.0.0"){{
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
            recursive_walk(json_dict)
        return file_list

    file_list: list[str] = recursive_walk(neuro_dict=json_file)

    for line in file_list:
        if not isinstance(line, str):
            continue
        if line.endswith(
            (
                "MP2RAGE.nii.gz",
                "UNIT1.nii.gz"
                # , ".bval", ".bvec"
            )
        ):
            continue
        path = tmp_path / line.strip()

        path.parent.mkdir(parents=True, exist_ok=True)
        if line.endswith(".json"):
            with open(path, "w") as file_handle:
                file_handle.write("{}")
        path.touch()
    print(path)
    spec = Spec(datetime.now, [])
    resolved_spec = ResolvedSpec(spec)

    file_obj = File(str(tmp_path), "bids")
    resolved_files = resolved_spec.resolve(file_obj)

    counter = 0
    for i in file_list:
        if (
            i.startswith("derivatives")
            or "/dwi" in i
            or i.endswith(("MP2RAGE.nii.gz", "UNIT1.nii.gz"))
        ):
            continue
        if i.endswith(("events.tsv", ".nii.gz", ".nii")):
            counter += 1
    assert counter == len(resolved_files)
