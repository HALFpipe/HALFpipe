from halfpipe.workflows.post_processing.factory import PostProcessingFactory


def test_init_setup(mock_post_processing_factory):
    """Check fmriprep_factory init and setup within fixture creation."""
    assert isinstance(mock_post_processing_factory, PostProcessingFactory)
    # TODO what to check w assert?

# TODO test connect etc
