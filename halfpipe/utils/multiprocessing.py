# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""
"""

from typing import Union

import os
from multiprocessing import get_context, active_children
from multiprocessing import pool as mpp

from ..logging import Context


def initializer(loggingargs, host_env):
    from ..logging import setup as setuplogging
    setuplogging(**loggingargs)

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
        initargs = (Context.loggingargs(), dict(os.environ))
        context = get_context("forkserver")
        super().__init__(
            processes=processes,
            initializer=initializer,
            initargs=initargs,
            maxtasksperchild=maxtasksperchild,
            context=context
        )

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        super().__exit__(exc_type, exc_value, traceback)
        self.join()
        terminate()
