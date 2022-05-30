# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

import pytest

from halfpipe.ingest.resolve import ResolvedSpec
from halfpipe.model import file
from halfpipe.model.file import base
from halfpipe.model.spec import Spec

from ...model.file.base import File
from ..resolve import ResolvedSpec


def test__resolve_bids(tmp_path: Path):
    cur_path = tmp_path
    # command = ["aws", "s3", "ls", "--recursive", "--no-sign-request", "s3://openneuro.org/ds004109", "|", "rev", "|", "cut", "-d\" \"", "-f1", "|", "rev", ">", "cur_path/all_files.txt"]
    # p = subprocess.run(command, shell=True)
    # Create empty directory
    new_file_dir_path = cur_path / "newfiles"
    if not os.path.exists(new_file_dir_path):
        os.makedirs(new_file_dir_path)
    file_path = (
        "/Users/dominik/all_files.txt"  # put in your text file from openneuro.org e.g.
    )
    # Create empty file for each file in all text file
    count = 0
    with open(file_path, "r") as f:
        for line in f:
            if not line.startswith("ds004109/sub"):
                continue
            new_file_dir_path.joinpath(str(line.strip)).touch()
            count += 1
            # pa.touch()
            # Path(new_file_dir_path/new_line).touch()
    file_obj = File(str(new_file_dir_path), "bids")
    spec_obj = Spec(datetime.now, [])
    resolved_spec_obj = ResolvedSpec(spec_obj)
    resolved_list = resolved_spec_obj.resolve(file_obj)
    # assert len(resolved_list) == len(ResolvedSpec._resolve_bids(self= spec_obj, fileobj= file_obj))
    assert count == len(resolved_list)
