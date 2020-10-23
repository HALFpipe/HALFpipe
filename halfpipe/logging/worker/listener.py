# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from marshmallow import ValidationError
from pathlib import Path

from asyncio import get_running_loop, all_tasks, current_task, gather

from .message import Message, MessageSchema
from .writer import PrintWriter, FileWriter

schema = MessageSchema()


async def listen(queue):
    from halfpipe.logging import setup as setuplogging
    setuplogging(queue)

    loop = get_running_loop()

    printWriter = PrintWriter(levelno=25)  # fmriprep's IMPORTANT
    logWriter = FileWriter(levelno=logging.DEBUG)
    errWriter = FileWriter(levelno=logging.WARNING)

    writers = [printWriter, logWriter, errWriter]

    [loop.create_task(writer.start()) for writer in writers]

    subscribers = [writer.queue for writer in writers]

    while True:
        message = await loop.run_in_executor(None, queue.get)

        # from pprint import pprint
        # pprint(schema.dump(message))

        if isinstance(message, Message):
            if len(schema.validate(message)) > 0:
                continue  # ignore invalid
        else:
            try:
                message = schema.load(message)
            except ValidationError:
                continue  # ignore invalid

        if message.type == "log":
            for subscriber in subscribers:
                await subscriber.put(message)

        elif message.type == "set_workdir":
            workdir = message.workdir

            if not isinstance(workdir, Path):
                workdir = Path(workdir)

            workdir.mkdir(exist_ok=True, parents=True)

            logWriter.filename = workdir / "log.txt"
            logWriter.canWrite.set()

            errWriter.filename = workdir / "err.txt"
            errWriter.canWrite.set()

        elif message.type == "enable_verbose":
            printWriter.levelno = logging.DEBUG

        elif message.type == "enable_print":
            printWriter.canWrite.set()

        elif message.type == "disable_print":
            printWriter.canWrite.clear()

        elif message.type == "teardown":
            # make sure that all writers have finished writing
            await gather(*[subscriber.join() for subscriber in subscribers])

            # then cancel all tasks
            tasks = [t for t in all_tasks() if t is not current_task()]

            [task.cancel() for task in tasks]

            await gather(*tasks)
            loop.stop()

            break

        queue.task_done()
