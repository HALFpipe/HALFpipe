# -*- coding: utf-8 -*-
from pathlib import Path


def test_start(snap_compare, bids_data: Path) -> None:
    assert snap_compare("../../src/start.py", press=["escape"], terminal_size=(204, 53))
