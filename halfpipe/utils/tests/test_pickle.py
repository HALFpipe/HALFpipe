# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from doctest import testfile
import pickle
import gzip
import lzma
import pytest
from ..pickle import load_pickle

@pytest.mark.parametrize(
    ('file_names', 'function_mode'),
    (
        ('test.pkl', open),
        ('test.pklz', gzip.open),
        ('test.pickle.xz', lzma.open),
    ),
)
def test_load_pickle(tmp_path, file_names, function_mode):
    test_list = ['hello', 'world']
    
    with function_mode(tmp_path / file_names, 'wb') as f:
        pickle.dump(test_list, f)
    with function_mode(tmp_path / file_names, 'rb') as f:
        test_files = pickle.load(f)
    
    assert load_pickle(tmp_path / file_names) == test_files
    """
    with open(tmp_path / 'test.pkl', 'wb') as f:
        pickle.dump(test_list, f)
    with open (tmp_path / 'test.pkl', 'rb') as f: 
        test_pickle = pickle.load(f)

    with gzip.open(tmp_path / 'test.pklz', 'wb') as f:
        pickle.dump(test_list, f)
        # gzip_compr = gzip.compress(f)
    with gzip.open(tmp_path / 'test.pklz', 'rb') as f:
        # f = gzip.decompress(gzip_compr)
        test_gzip = pickle.load(f)

    with lzma.open(tmp_path / 'test.pickle.xz', 'wb') as f:
        pickle.dump(test_list, f)
        # lzma_compr = lzma.compress(f)
    with lzma.open(tmp_path / 'test.pickle.xz', 'rb') as f:
        # f = lzma.decompress(lzma_compr)
        test_lzma = pickle.load(f)
    assert load_pickle(tmp_path / 'test.pkl') ==  test_pickle
    assert load_pickle(tmp_path / 'test.pklz') == test_gzip
    assert load_pickle(tmp_path / 'test.pickle.xz') == test_lzma
    """