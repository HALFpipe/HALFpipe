# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from ..ingest.database import Database
from ..logging import logger


def collect_events(database: Database, source_file: str) -> tuple[str | tuple[str, str], ...] | None:
    task = database.tagval(source_file, "task")
    if not isinstance(task, str):
        logger.warning(f'Cannot collect events for "{source_file}" because it has no task tag')
        return None
    # Get from database
    candidates: tuple[str, ...] | None = database.associations(
        source_file,
        task=task,  # Enforce same task
        datatype="func",
        suffix="events",
    )
    if candidates is None or len(candidates) == 0:
        return None

    # Filter
    condition_files: list[str | tuple[str, str]] = list()

    source_file_subject = database.tagval(source_file, "sub")
    for candidate in sorted(set(candidates)):  # remove duplicates
        # enforce same subject if applicable
        subject = database.tagval(candidate, "sub")
        if subject is not None:
            if subject != source_file_subject:
                continue

        extension = database.tagval(candidate, "extension")
        if extension == ".txt":
            condition = database.tagval(candidate, "condition")
            assert isinstance(condition, str)
            condition_file: str | tuple[str, str] = (candidate, condition)
        else:
            condition_file = candidate

        condition_files.append(condition_file)

    if len(condition_files) > 0:
        return tuple(condition_files)
    else:
        return None
