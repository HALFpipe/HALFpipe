import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Assign each test to one of three xdist groups depending on how long it takes to run."""
    for item in items:
        name = item.name
        if "[" in name:  # strip parametrization
            name = name[: name.index("[")]

        if name == "test_feature_extraction":
            group = "feature_extraction"
        elif item.get_closest_marker("slow") is not None:
            group = "slow"
        else:
            group = "fast"

        item.add_marker(pytest.mark.xdist_group(group))
