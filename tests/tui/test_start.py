# -*- coding: utf-8 -*-


def test_start(snap_compare):
    assert snap_compare("../../src/start.py", press=["escape"], terminal_size=(204, 53))
