# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Mapping

import pytest
from halfpipe.exclude import Decision, QCDecisionMaker


# include = 1 exclude = 2
@pytest.mark.parametrize(
    "tags, decision",
    [
        ({"rating": "good", "rating1": "good"}, Decision.INCLUDE),
        ({"rating": "bad", "rating1": "bad"}, Decision.EXCLUDE),
        ({"rating": "good", "rating1": "bad"}, Decision.EXCLUDE),
        ({"rating": "good", "rating1": "uncertain"}, Decision.INCLUDE),
        ({"rating": "good", "rating1": "none"}, Decision.INCLUDE),
        ({"rating": "bad", "rating1": "uncertain"}, Decision.EXCLUDE),
        ({"rating": "bad", "rating1": "none"}, Decision.EXCLUDE),
        ({"rating": "uncertain", "rating1": "none"}, Decision.INCLUDE),
    ],
)
def test_get(tmp_path, tags: Mapping[str, str], decision):
    file_paths: list[Path] = []
    test_file_path = tmp_path / "exclude_hcp_neele.json"
    x = (
        {
            "sub": "PSY_00",
            "type": "skull_strip_report",
            "rating": tags["rating"],
        },
        {
            "sub": "PSY00",
            "type": "t1_norm_rpt",
            "rating": tags["rating1"],
        },
    )

    with open(test_file_path, "w") as file_handle:
        json.dump(x, file_handle)

    file_paths.append(test_file_path)
    # warnings catcher & tasks maybe 2nd test
    qc = QCDecisionMaker(file_paths=file_paths)
    assert qc.get(tags=dict(sub="PSY00")) == decision
    assert qc.get(tags=dict(sub="PSY_00")) == decision
    assert qc.get(tags=dict(sub="sub-PSY00")) == decision
    assert qc.get(tags=dict(sub="sub-PSY00", run=["03"])) == decision
