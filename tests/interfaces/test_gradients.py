def test_brainspace_install():
    """ Test if brainspace is installed."""
    try:
        import brainspace
    except ImportError:
        raise ImportError(f'Install "brainspace".')