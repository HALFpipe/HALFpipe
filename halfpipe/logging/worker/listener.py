# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from pathlib import Path
from copy import deepcopy

from asyncio import get_running_loop, all_tasks, current_task, gather

from .message import (
    DisablePrintMessage,
    EnablePrintMessage,
    EnableVerboseMessage,
    LogMessage,
    SetWorkdirMessage,
    TeardownMessage,
)
from .writer import PrintWriter, FileWriter, ReportErrorWriter
from ...utils import logger


async def listen(queue):
    from halfpipe.logging import setup as setup_logging
    setup_logging(queue)

    loop = get_running_loop()

    printWriter = PrintWriter(levelno=25)  # fmriprep's IMPORTANT
    logWriter = FileWriter(levelno=logging.DEBUG)
    errWriter = FileWriter(levelno=logging.WARNING)
    reportErrWriter = ReportErrorWriter(levelno=logging.ERROR)

    writers = [printWriter, logWriter, errWriter, reportErrWriter]

    [loop.create_task(writer.start()) for writer in writers]

    subscribers = [writer.queue for writer in writers]

    while True:
        message = await loop.run_in_executor(None, queue.get)

        if isinstance(message, LogMessage):
            for subscriber in subscribers:
                messagecopy = deepcopy(message)  # allow subscribers to modify message
                await subscriber.put(messagecopy)

        elif isinstance(message, SetWorkdirMessage):
            workdir: Path = message.workdir

            workdir.mkdir(exist_ok=True, parents=True)

            logWriter.filename = workdir / "log.txt"
            logWriter.canWrite.set()

            errWriter.filename = workdir / "err.txt"
            errWriter.canWrite.set()

            reportErrWriter.filename = workdir / "reports" / "reporterror.js"
            reportErrWriter.canWrite.set()

        elif isinstance(message, EnableVerboseMessage):
            printWriter.levelno = logging.DEBUG

        elif isinstance(message, EnablePrintMessage):
            printWriter.canWrite.set()

        elif isinstance(message, DisablePrintMessage):
            printWriter.canWrite.clear()

        elif isinstance(message, TeardownMessage):
            # make sure that all writers have finished writing
            await gather(*[subscriber.join() for subscriber in subscribers])

            # then cancel all tasks
            tasks = [t for t in all_tasks() if t is not current_task()]

            [task.cancel() for task in tasks]

            await gather(*tasks)
            loop.stop()

            break

        else:
            logger.error(f'Logging worker received unknown message "{message}"')

        queue.task_done()
