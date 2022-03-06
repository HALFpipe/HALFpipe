# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

import multiprocessing.pool as mpp
import os
from multiprocessing import active_children, get_context
from typing import Union

from ..logging import logging_context


def initializer(logging_args, host_env):
    from ..logging import setup as setup_logging

    setup_logging(**logging_args)

    os.environ.update(host_env)


def terminate():
    for p in active_children():
        p.terminate()
        p.join()


class Pool(mpp.Pool):
    def __init__(
        self,
        processes: Union[int, None] = None,
        maxtasksperchild: Union[int, None] = None,
    ) -> None:
        initargs = (logging_context.logging_args(), dict(os.environ))
        context = get_context("forkserver")
        super().__init__(
            processes=processes,
            initializer=initializer,
            initargs=initargs,
            maxtasksperchild=maxtasksperchild,
            context=context,
        )

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        super().__exit__(exc_type, exc_value, traceback)
        self.join()
