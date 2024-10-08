# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import zipfile
from pathlib import Path

import pytest
from nipype.interfaces.base.support import Bunch

from halfpipe.utils.path import find_paths, recursive_list_directory, split_ext

A = "/tmp/a.txt"  # TODO make this more elegant with a tmp_dir
B = "/tmp/b.txt"


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "obj",
    [
        [A, B],
        (A, B),
        {A, B},
        {"a": A, "b": B},
        {"x": {"y": [A, B]}},
        Bunch(a=A, b=B),
        Bunch(x=[A, B]),
    ],
)
def test_find_paths(tmp_path, obj):
    os.chdir(str(tmp_path))

    for fname in [A, B]:
        Path(fname).touch()

    assert set(find_paths(obj)) == set([A, B])

    for fname in [A, B]:
        Path(fname).unlink()


def test_split_ext():
    assert split_ext("a/a.nii.gz") == ("a", ".nii.gz")
    assert split_ext("a/a.pickle.xz") == ("a", ".pickle.xz")


def test_recursive_list_directory(tmp_path: Path) -> None:
    # Create some files and directories to test with
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.txt").touch()
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir2").mkdir()
    (tmp_path / "dir1" / "file3.txt").touch()
    (tmp_path / "dir2" / "file4.txt").touch()
    tmp_paths = {
        tmp_path / "file1.txt",
        tmp_path / "file2.txt",
        tmp_path / "dir1",
        tmp_path / "dir2",
        tmp_path / "dir1" / "file3.txt",
        tmp_path / "dir2" / "file4.txt",
    }

    # Test that all files and directories are returned
    assert set(recursive_list_directory(tmp_path)) == tmp_paths

    # Test that only directories are returned when only_directories=True
    assert set(recursive_list_directory(tmp_path, only_directories=True)) == {
        tmp_path / "dir1",
        tmp_path / "dir2",
    }

    # Test that archives are entered when enter_archives=True
    zip_file1_path = tmp_path / "zip_file1.zip"
    with zipfile.ZipFile(zip_file1_path, "w") as zip_file:
        zip_file.write(tmp_path / "file1.txt", "file5.txt")
        zip_file.write(tmp_path / "file1.txt", "dir3/file6.txt")
    zip_file1_paths = [
        zipfile.Path(zip_file1_path) / "file5.txt",
        zipfile.Path(zip_file1_path) / "dir3",
        zipfile.Path(zip_file1_path) / "dir3" / "file6.txt",
    ]
    tmp_and_zip_paths = [
        *tmp_paths,
        zip_file1_path,
        *zip_file1_paths,
    ]
    assert set(map(str, recursive_list_directory(tmp_path, enter_archives=True))) == set(map(str, tmp_and_zip_paths))

    # # Test nested archives
    # zip_file2_path = tmp_path / "zip_file2.zip"
    # with zipfile.ZipFile(zip_file2_path, "w") as zip_file:
    #     zip_file.write(tmp_path / "file1.txt", "file7.txt")
    #     zip_file.write(zip_file1_path, "zip_file1.zip")
    # tmp_and_zip_paths.append(zip_file2_path)
    # tmp_and_zip_paths.append(zipfile.Path(zip_file2_path) / "file7.txt")
    # tmp_and_zip_paths.extend(
    #     zipfile.Path(zip_file2_path) / "zip_file1.zip" / path.at for path in zip_file1_paths
    # )
    # assert set(
    #     map(str, recursive_list_directory(tmp_path, enter_archives=True))
    # ) == set(map(str, tmp_and_zip_paths))

    # Test that max_depth works
    assert set(recursive_list_directory(tmp_path, max_depth=1)) == {
        tmp_path / "file1.txt",
        tmp_path / "file2.txt",
        zip_file1_path,
        tmp_path / "dir1",
        tmp_path / "dir2",
    }
