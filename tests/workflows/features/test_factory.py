from halfpipe.workflows.features.factory import FeatureFactory


def test_init_setup(mock_feature_factory):
    """Check feature_factory init and setup within fixture creation."""
    assert isinstance(mock_feature_factory, FeatureFactory)
    # TODO what to check w assert?


# TODO test connect etc
