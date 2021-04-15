# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from logging import Filter
import re


def setLevel(record, levelno=logging.DEBUG):
    record.levelno = levelno
    record.levelname = logging.getLevelName(levelno)


class DTypeWarningsFilter(Filter):
    regex = re.compile(r"Changing (.+) dtype from (.+) to (.+)")

    def filter(self, record):
        message = record.getMessage()

        if self.regex.search(message) is not None:
            setLevel(record, levelno=logging.INFO)

        return True


pywarnings_to_ignore = [
    "the matrix subclass is not the recommended way to represent matrices or deal with linear algebra (see https://docs.scipy.org/doc/numpy/user/numpy-for-matlab-users.html). Please adjust your code to use regular ndarray.",
    "cmp not installed",
    "dist() and linux_distribution() functions are deprecated in Python 3.5",
    "The trackvis interface has been deprecated and will be removed in v4.0; please use the 'nibabel.streamlines' interface.",
    "This has not been fully tested. Please report any failures.",
    "future versions will not create a writeable array from broadcast_array. Set the writable flag explicitly to avoid this warning.",
    "The ability to pass arguments to BIDSLayout that control indexing is likely to be removed in future; possibly as early as PyBIDS 0.14. This includes the `config_filename`, `ignore`, `force_index`, and `index_metadata` arguments. The recommended usage pattern is to initialize a new BIDSLayoutIndexer with these arguments, and pass it to the BIDSLayout via the `indexer` argument.",
    "genfromtxt: Empty input file:",
    "Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated, and in 3.8 it will stop working",
    "Using a non-tuple sequence for multidimensional indexing is deprecated; use `arr[tuple(seq)]` instead of `arr[seq]`. In the future this will be interpreted as an array index, `arr[np.array(seq)]`, which will result either in an error or a different result.",
    "`rcond` parameter will change to the default of machine precision times ``max(M, N)`` where M and N are the input matrix dimensions.",
    "was deprecated in Matplotlib 3.3 and will be removed two minor releases later.",
    "The label function will be deprecated in a future version. Use Tick.label1 instead.",
    "The behaviour of affine_transform with a one-dimensional array supplied for the matrix parameter has changed in scipy 0.18.0.",
    "No contour levels were found within the data range.",
    "Support for setting the 'mathtext.fallback_to_cm' rcParam is deprecated since 3.3 and will be removed two minor releases later; use 'mathtext.fallback : 'cm' instead.",
    "VisibleDeprecationWarning: Creating an ndarray from ragged nested sequences (which is a list-or-tuple of lists-or-tuples-or ndarrays with different lengths or shapes) is deprecated.",
    "FutureWarning: Index.ravel returning ndarray is deprecated; in a future version this will return a view on self.",
    "FutureWarning: Fetchers from the nilearn.datasets module will be updated in version 0.9 to return python strings instead of bytes and Pandas dataframes instead of Numpy arrays",
    "`np.bool` is a deprecated alias for the builtin `bool`. To silence this warning, use `bool` by itself. Doing this will not modify any behavior and is safe. If you specifically wanted the numpy scalar type, use `np.bool_` here.",
    "`np.int` is a deprecated alias for the builtin `int`. To silence this warning, use `int` by itself. Doing this will not modify any behavior and is safe. When replacing `np.int`, you may wish to use e.g. `np.int64` or `np.int32` to specify the precision. If you wish to review your current use, check the release note link for additional information.",
    "`np.float` is a deprecated alias for the builtin `float`. To silence this warning, use `float` by itself. Doing this will not modify any behavior and is safe. If you specifically wanted the numpy scalar type, use `np.float64` here.",
    "numpy.ufunc size changed, may indicate binary incompatibility.",
    "RequestsDependencyWarning",
    "In future, it will be an error for 'np.bool_' scalars to be interpreted as an index",
]


class PyWarningsFilter(Filter):

    def __init__(self) -> None:
        super().__init__(name="pywarnings_filter")

        escaped = list(map(str, map(re.escape, pywarnings_to_ignore)))
        regex_str = "|".join(escaped)
        self.regex = re.compile(f"(?:{regex_str})")

    def filter(self, record):
        message = record.getMessage()

        if self.regex.search(message) is not None:
            setLevel(record, levelno=logging.DEBUG)

        if "invalid value encountered in" in message:  # make sqrt and division errors less visible
            setLevel(record, levelno=logging.INFO)

        return True
