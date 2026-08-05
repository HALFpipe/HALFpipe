from halfpipe.collect.bold import collect_bold_files
from halfpipe.ingest.database import Database
from halfpipe.workflows.fmriprep.factory import FmriprepFactory


def test_collect_bold_files(tmp_path, bids_data, mock_spec):
    """Check if collected bold files is empty."""
    database = Database(mock_spec, bids_database_dir=bids_data)

    bold_file_paths_dict = collect_bold_files(mock_spec, database)
    assert len(bold_file_paths_dict) > 0


def test_init_setup(mock_fmriprep_factory):
    """Check fmriprep_factory init and setup within fixture creation."""
    fmriprep_factory = mock_fmriprep_factory[0]

    assert isinstance(fmriprep_factory, FmriprepFactory)
    # TODO what to check w assert?


# TODO test connect etc
