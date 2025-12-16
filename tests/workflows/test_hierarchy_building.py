import pytest

from halfpipe.workflows.base import init_workflow

# from halfpipe.logging.context import Context, setup as setup_logging


@pytest.mark.parametrize(
    "bids_session_expanded_real_test_data",
    [1, 4],
    indirect=True,
    ids=["no_sessions", "four_sessions"],
)
def test_init_workflow_parallel_safe(bids_session_expanded_real_test_data):
    data_path, workdir_path = bids_session_expanded_real_test_data
    # Just check workflow runs
    init_workflow(workdir_path)
