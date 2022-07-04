# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import string
from datetime import datetime
from pathlib import Path
from typing import List

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
    # Test different IDs with .parametrize or string.Template substitute method
    query_example = f"""query{{
        dataset (id: "{openneuroID}"){{
            latestSnapshot{{
                id
                files(prefix: null){{
                    filename
                }}
            }}
        }}
    }}"""
    gql_url = "https://openneuro.org/crn/graphql"
    r = requests.post(gql_url, json={"query": query_example})
    if not r == 200:
        print(r.status_code)

    file_list: List[str] = []
    json_file = json.loads(r.text)
    for val in json_file["data"]["dataset"]["latestSnapshot"]["files"]:
        file_list.append(val["filename"])

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
