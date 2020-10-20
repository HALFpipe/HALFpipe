# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from logging import Filter
import re


class DTypeWarningsFilter(Filter):
    regex = re.compile(r"Changing (.+) dtype from (.+) to (.+)")

    def filter(self, record):
        message = record.getMessage()

        if self.regex.search(message) is not None:
            record.level = logging.INFO

        return True


class PyWarningsFilter(Filter):
    messages_to_filter = frozenset(
        (
            "WARNING: the matrix subclass is not the recommended way to represent matrices or deal with linear algebra (see https://docs.scipy.org/doc/numpy/user/numpy-for-matlab-users.html). Please adjust your code to use regular ndarray.",
            "WARNING: cmp not installed",
            "WARNING: dist() and linux_distribution() functions are deprecated in Python 3.5",
            "WARNING: The trackvis interface has been deprecated and will be removed in v4.0; please use the 'nibabel.streamlines' interface.",
            "WARNING: This has not been fully tested. Please report any failures.",
            "WARNING: future versions will not create a writeable array from broadcast_array. Set the writable flag explicitly to avoid this warning.",
            "WARNING: The ability to pass arguments to BIDSLayout that control indexing is likely to be removed in future; possibly as early as PyBIDS 0.14. This includes the `config_filename`, `ignore`, `force_index`, and `index_metadata` arguments. The recommended usage pattern is to initialize a new BIDSLayoutIndexer with these arguments, and pass it to the BIDSLayout via the `indexer` argument.",
        )
    )

    def filter(self, record):
        message = record.getMessage()

        if message in self.messages_to_filter:
            record.level = logging.DEBUG
        elif message.startswith("WARNING: genfromtxt: Empty input file:"):
            record.level = logging.DEBUG
        elif "Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated, and in 3.8 it will stop working" in message:
            record.level = logging.DEBUG

        return True
