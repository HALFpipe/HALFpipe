import pytest

from halfpipe.workflows.base import init_workflow

# from halfpipe.logging.context import Context, setup as setup_logging


@pytest.mark.parametrize(
    "bids_season_test_data",
    [[], ["01", "02"], ["01", "02", "03", "04"]],
    indirect=True,
    ids=["no_sessions", "two_sessions", "four_sessions"],
)
def test_init_workflow_parallel_safe(bids_season_test_data):
    data_path, workdir_path = bids_season_test_data
    # Just check workflow runs
    init_workflow(workdir_path)
