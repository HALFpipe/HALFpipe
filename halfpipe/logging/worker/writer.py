# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from abc import abstractmethod
import sys
import re

from pathlib import Path

from asyncio import get_running_loop, Queue, QueueEmpty, Event, CancelledError, sleep

from flufl.lock import Lock

from .message import Message

escapeCodesRegex = re.compile(r"\x1b\[.*?(m|K)")


class Writer:
    """
    """

    terminator = "\n"

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

        try:
            while True:
                await self.canWrite.wait()

                if not self.check():
                    self.canWrite.clear()

                    continue

                try:
                    message = await self.queue.get()

                    if not self.filterMessage(message):
                        self.queue.task_done()
                        continue  # avoid acquiring the lock

                    await loop.run_in_executor(None, self.acquire)

                    while True:
                        if self.filterMessage(message):
                            await loop.run_in_executor(
                                None, self.emit, message.msg, message.levelno
                            )
                        self.queue.task_done()

                        try:  # handle any other records while we have the lock
                            message = self.queue.get_nowait()
                        except QueueEmpty:
                            break

                    await loop.run_in_executor(None, self.release)

                    await sleep(1.0)  # rate limit
                except Exception:
                    self.canWrite.clear()

        except CancelledError:
            pass

    def check(self) -> bool:
        return True

    def acquire(self):
        pass

    @abstractmethod
    def emit(self, msg: str, levelno: int):
        raise NotImplementedError()

    def release(self):
        pass


class PrintWriter(Writer):
    def emit(self, msg: str, levelno: int):
        # if levelno >= logging.WARNING:
        #     sys.stderr.write(msg + self.terminator)
        # else:
        sys.stdout.write(msg + self.terminator)

    def release(self):
        sys.stdout.flush()
        # sys.stderr.flush()


class FileWriter(Writer):
    def __init__(self, **kwargs):
        super(FileWriter, self).__init__(**kwargs)

        self.filename = None

        self.stream = None
        self.lock = None

    def check(self) -> bool:
        if self.filename is None or not isinstance(self.filename, Path):
            return False

        return True

    def acquire(self):
        lock_file = str(self.filename.parent / f".{self.filename.name}.lock")  # hidden lock file

        self.lock = Lock(lock_file, lifetime=60)  # seconds after which the lock is broken
        self.lock.lock(timeout=None)  # try forever

        self.stream = open(self.filename, mode="a", encoding="utf-8")

    def emit(self, msg: str, levelno: int):
        msg = escapeCodesRegex.sub("", msg)
        self.stream.write(msg + self.terminator)

    def release(self):
        self.stream.close()

        self.lock.unlock(unconditionally=True)  # do not raise errors in unlock
        self.lock = None
