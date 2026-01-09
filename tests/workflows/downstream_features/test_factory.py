from halfpipe.workflows.downstream_features.factory import DownstreamFeatureFactory


def test_init_setup(mock_downstream_feature_factory):
    """Check downstream_feature_factory init and setup within fixture creation."""
    assert isinstance(mock_downstream_feature_factory, DownstreamFeatureFactory)
    # TODO what to check w assert?

# TODO test connect etc