# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from abc import abstractmethod
from asyncio import CancelledError, Event, Queue, QueueEmpty, get_running_loop, sleep

from ..message import LogMessage


class Writer:
    """ """

    terminator = "\n"

    def __init__(self, levelno=logging.DEBUG):
        self.queue: Queue = Queue()
        self.can_write = Event()
        self.levelno = levelno

    @property
    def delay(self) -> float:
        return 1.0

    def filter_message(self, message: LogMessage) -> bool:
        if not isinstance(message, LogMessage):
            return False  # ignore invalid

        if message.levelno is not None and message.levelno < self.levelno:
            return False  # filter level

        return True

    async def start(self):
        loop = get_running_loop()

        while True:
            try:
                await self.can_write.wait()

                if not self.check():
                    self.can_write.clear()

                    continue

                message = await self.queue.get()

                await self.can_write.wait()

                if not self.filter_message(message):
                    self.queue.task_done()
                    continue  # avoid acquiring the lock

                await loop.run_in_executor(None, self.acquire)

                while True:
                    if self.filter_message(message):
                        await loop.run_in_executor(None, self.emit_message, message)
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
        logging.warning(f"Caught exception in {self.__class__.__name__}. Stopping", exc_info=True)
        self.can_write.clear()

    def check(self) -> bool:
        return True

    def acquire(self):
        pass

    def emit_message(self, message: LogMessage):
        msg = message.long_msg
        levelno = message.levelno

        self.emit(msg, levelno)

    @abstractmethod
    def emit(self, msg: str, levelno: int):
        raise NotImplementedError()

    def release(self):
        pass
