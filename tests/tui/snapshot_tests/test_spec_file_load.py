# -*- coding: utf-8 -*-

from functools import partial
from pathlib import Path

import pytest

from ..spec_file_load_flow import run_before


@pytest.mark.forked
def test_load_from_spec_file_f0(
    snap_compare,
    start_app,
    spec_file_dir_path: Path,
    downloaded_data_path: Path,
    atlases_maps_seed_images_path: Path,
    covariant_spreadsheet_path: Path,
    feature_label: str = "taskBased_1",
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        covariant_spreadsheet_path=covariant_spreadsheet_path,
        feature_label=feature_label,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f1(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "taskBased_2"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, spec_file_dir_path=spec_file_dir_path, feature_label=feature_label
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f2(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "seedCorr_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, spec_file_dir_path=spec_file_dir_path, feature_label=feature_label
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f3(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "dualReg_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, spec_file_dir_path=spec_file_dir_path, feature_label=feature_label
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f4(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "corrMatrix_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before, data_path=downloaded_data_path, spec_file_dir_path=spec_file_dir_path, feature_label=feature_label
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f5(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "reHo_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        feature_label=feature_label,
        scroll_to_remaining_part=True,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f6(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "fALFF_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        feature_label=feature_label,
        scroll_to_remaining_part=True,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f7(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "fALFF_2"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        feature_label=feature_label,
        scroll_to_remaining_part=True,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


@pytest.mark.forked
def test_load_from_spec_file_f8(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, feature_label: str = "preproc_1"
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        feature_label=feature_label,
        scroll_to_remaining_part=True,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


from pathlib import Path


def test_load_from_spec_file_resave_spec_file(
    snap_compare, start_app, spec_file_dir_path: Path, downloaded_data_path: Path, covariant_spreadsheet_path: Path
) -> None:
    """Check whether one can set the working directory."""
    run_before_with_extra_args = partial(
        run_before,
        data_path=downloaded_data_path,
        spec_file_dir_path=spec_file_dir_path,
        covariant_spreadsheet_path=covariant_spreadsheet_path,
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
