# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import abstractmethod

from asyncio import get_running_loop, Queue, QueueEmpty, Event, CancelledError, sleep

import logging
import sys

from ..message import Message


class Writer:
    """
    """

    terminator = "\n"

    delay = 1.0

    def __init__(self, levelno=logging.DEBUG):
        self.queue = Queue()
        self.canWrite = Event()
        self.levelno = levelno

    def filterMessage(self, message) -> bool:
        if not isinstance(message, Message) or message.type != "log":
            return False  # ignore invalid

        if message.levelno < self.levelno:
            return False  # filter level

        return True

    async def start(self):
        loop = get_running_loop()

        while True:
            try:
                await self.canWrite.wait()

                if not self.check():
                    self.canWrite.clear()

                    continue

                message = await self.queue.get()

                if not self.filterMessage(message):
                    self.queue.task_done()
                    continue  # avoid acquiring the lock

                await loop.run_in_executor(None, self.acquire)

                while True:
                    if self.filterMessage(message):
                        await loop.run_in_executor(None, self.emitmessage, message)
                    self.queue.task_done()

                    try:  # handle any other records while we have the lock
                        message = self.queue.get_nowait()
                    except QueueEmpty:
                        break

                await loop.run_in_executor(None, self.release)

                await sleep(self.delay)  # rate limit

            except CancelledError:
                break  # exit the writer

            except Exception:  # catch all
                self.exception()

    def exception(self):
        logging.warning(
            f"Caught exception in {self.__class__.__name__}. Stopping",
            exc_info=True
        )
        self.canWrite.clear()

    def check(self) -> bool:
        return True

    def acquire(self):
        pass

    def emitmessage(self, message: Message):
        msg = message.msg
        levelno = message.levelno

        assert isinstance(msg, str)
        assert isinstance(levelno, int)

        self.emit(msg, levelno)

    @abstractmethod
    def emit(self, msg: str, levelno: int):
        raise NotImplementedError()

    def release(self):
        pass
