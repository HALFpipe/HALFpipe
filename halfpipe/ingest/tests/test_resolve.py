# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import string
from datetime import datetime
from pathlib import Path
from typing import List

import requests

from ...model.file.base import File
from ...model.spec import Spec
from ..resolve import ResolvedSpec


def test__resolve_bids(tmp_path: Path):
    # command = ["aws", "s3", "ls", "--recursive", "--no-sign-request", "s3://openneuro.org/ds004109", "|", "rev", "|", "cut", "-d\" \"", "-f1", "|", "rev", ">", "cur_path/all_files.txt"]
    # p = subprocess.run(command, shell=True)

    # Create empty directory
    file_path = "/Users/dominik/all_files.txt"
    # "/home/lea/downloads/all_files.txt"  # put in your text file from openneuro.org e.g.

    # Create empty file for each file in all text file
    """with open(file_path, "r") as file_handle:
        lines = file_handle.readlines()

    for line in lines:
        path = tmp_path / line.strip()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        """

    # Get file names with GraphQL request
    # Test different IDs with .parametrize or string.Template substitute method
    query_example = """query{
        dataset(id: "ds004109"){
            latestSnapshot{
                id
                files(prefix: null){
                    filename
                }
            }
        }
    }"""
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

    assert len(file_list) == len(resolved_files)
