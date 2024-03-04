# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from multiprocessing import cpu_count
from pathlib import Path

import pytest
from fmriprep import config
from halfpipe.model.file.schema import FileSchema
from halfpipe.model.spec import Spec
from halfpipe.workflows.base import init_workflow
from halfpipe.workflows.execgraph import init_execgraph

from tests.workflows.spec import make_spec

from .datasets import Dataset, datasets, download_dataset


@pytest.mark.parametrize("dataset", datasets)
def test_download_dataset(tmp_path: Path, dataset: Dataset):
    original_log_level = logging.getLogger().getEffectiveLevel()
    logging.basicConfig(level=logging.DEBUG, force=True)
    downloaded_datasets = download_dataset(tmp_path, dataset)
    logging.getLogger().setLevel(original_log_level)  # Reset the logging level to its original state

    assert Path(downloaded_datasets.path).exists(), f"Dataset directory {downloaded_datasets.path} does not exist"
    for expected_path in dataset.paths:
        file_path = tmp_path / expected_path
        assert file_path.exists(), f"Expected file {file_path} does not exist in the dataset {dataset.name} "

    return downloaded_datasets


@pytest.fixture(scope="function")
def consistency_spec(bids_data: Path, pcc_mask: Path) -> Spec:
    """
    Create a new fixture for test_constistency. This creates the same spec
    for each dataset and returns it.
    Todo: feed the paths of downloaded_datasets
    """
    bids_file = FileSchema().load(
        dict(datatype="bids", path=str(bids_data)),
    )
    consistency_spec = make_spec(
        dataset_files=[bids_file],
        pcc_mask=pcc_mask,
    )

    return consistency_spec


# @pytest.mark.parametrize("dataset", datasets)  # Need to run the same test for each bids directory
@pytest.mark.skip(reason="Skipping feature extraction until fixture is created")
def test_extraction(bids_data: Path, pcc_mask: Path, tmp_path) -> Spec:
    """
    Run preprocessing and feature extraction for each of the three participants
    """

    config.nipype.omp_nthreads = cpu_count()

    workflow = init_workflow(tmp_path)

    graphs = init_execgraph(tmp_path, workflow)
    graph = next(iter(graphs.values()))

    assert any("sdc_estimate_wf" in u.fullname for u in graph.nodes)

    return consistency_spec


def test_compare_consistency():
    """
    Compare consistency between
    """
    pass
