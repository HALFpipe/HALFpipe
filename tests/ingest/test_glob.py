# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from random import choices, seed
from string import ascii_lowercase, digits

from halfpipe.ingest.glob import tag_glob


def _random_string(length: int = 5) -> str:
    return "".join(choices(ascii_lowercase + digits, k=length))


def test_tag_glob(tmp_path: Path) -> None:
    seed(a=0x5E6128C4)

    ground_truth: dict[str, dict[str, int]] = dict()

    for i in range(10):
        for j in range(1, 3):
            file_path = tmp_path / f"sub-{i:02d}" / f"{_random_string()}_T1w_{_random_string()}_run-{j:02d}.txt"
            file_path.parent.mkdir(exist_ok=True)
            file_path.touch()

            ground_truth[str(file_path)] = dict(subject=i, run=j)

            file_path = tmp_path / f"sub-{i:02d}" / f"{_random_string()}_T2w_{_random_string()}_run-{j:02d}.txt"
            file_path.parent.mkdir(exist_ok=True)
            file_path.touch()

    path_pattern = str(tmp_path / "sub-{subject}" / "*_T1w_*_run-{run}.txt")

    matched_file_paths = set()

    for file_str, tag_dict in tag_glob(path_pattern, entities=["subject", "run"]):
        assert file_str in ground_truth
        gt = ground_truth[file_str]
        assert set(gt.keys()) == set(tag_dict.keys())

        a = set(gt.items())
        b = set((entity, int(value)) for entity, value in tag_dict.items())
        assert a == b

        matched_file_paths.add(file_str)

    assert set(ground_truth.keys()) == matched_file_paths
