# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import multiprocessing.pool as mp_pool
import os
from multiprocessing import active_children, get_context
from typing import Any

mp_context = get_context("spawn")


def mock_tqdm(iterable, *args, **kwargs):
    return iterable


def get_init_args() -> tuple[set[int], dict[str, Any], dict[str, str], str]:
    from ..logging.base import logging_context

    return (
        os.sched_getaffinity(0),
        logging_context.logging_args(),
        dict(os.environ),
        os.getcwd(),
    )


def initializer(
    sched_affinity: set[int],
    logging_kwargs: dict[str, Any],
    host_env: dict[str, str],
    host_cwd: str,
) -> None:
    os.sched_setaffinity(0, sched_affinity)

    os.chdir(host_cwd)

    # Do not show tqdm progress bars from subprocesses
    import tqdm
    import tqdm.auto

    tqdm.tqdm = mock_tqdm
    tqdm.auto.tqdm = mock_tqdm

    # Make sure we send all logging to the logger process
    from ..logging.base import setup as setup_logging

    setup_logging(**logging_kwargs)

    # Make sure we use the same environment variables as the parent process
    os.environ.update(host_env)


def terminate() -> None:
    for p in active_children():
        p.terminate()
        p.join()


class Pool(mp_pool.Pool):
    def __init__(
        self,
        processes: int | None = None,
        maxtasksperchild: int | None = None,
    ) -> None:
        init_args = get_init_args()
        super().__init__(
            processes=processes,
            initializer=initializer,
            initargs=init_args,
            maxtasksperchild=maxtasksperchild,
            context=mp_context,
        )

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        super().__exit__(exc_type, exc_value, traceback)
        self.join()
