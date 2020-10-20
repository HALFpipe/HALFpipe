# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys

import logging
from pathlib import Path
from multiprocessing import SimpleQueue
from threading import RLock

from .worker import Worker, MessageSchema

schema = MessageSchema()


class Context(object):
    _instance = None
    _instance_rlock = RLock()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            with cls._instance_rlock:
                if cls._instance is None:
                    cls._instance = cls()

        return cls._instance

    @classmethod
    def teardown(cls):
        with cls._instance_rlock:
            if cls._instance is not None:
                # cls._instance.loop.teardown()
                pass

    @classmethod
    def queue(cls):
        return cls.instance().queue

    @classmethod
    def loggingargs(cls):
        return dict(
            queue=cls.queue(),
            levelno=logging.getLogger("halfpipe").handlers[0].level
        )

    @classmethod
    def enableDebug(cls):
        pass

    @classmethod
    def enableVerbose(cls):
        obj = schema.dump({"type": "enable_verbose"})
        cls.queue().put(obj)

    @classmethod
    def enablePrint(cls):
        obj = schema.dump({"type": "enable_print"})
        cls.queue().put(obj)

    @classmethod
    def disablePrint(cls):
        obj = schema.dump({"type": "disable_print"})
        cls.queue().put(obj)

    @classmethod
    def setWorkdir(cls, workdir):
        obj = schema.dump({"type": "set_workdir", "workdir": workdir})
        cls.queue().put(obj)

    def __init__(self):
        self.queue = SimpleQueue()

        worker = Worker(self.queue)
        worker.start()

        # self.stdoutwriter = StreamWriter(queuepublisher, sys.stdout)
        # queuepublisher.subscribe(self.stdoutwriter.queue, 25)
        # self.loop.run_coroutine_threadsafe(self.stdoutwriter.start)

        # self.logtxthandler = FileWriter()
        # queuepublisher.subscribe(self.logtxthandler.queue, logging.DEBUG)
        # self.loop.run_coroutine_threadsafe(self.logtxthandler.start)

        # self.errtxthandler = FileWriter()
        # queuepublisher.subscribe(self.errtxthandler.queue, logging.WARNING)
        # self.loop.run_coroutine_threadsafe(self.errtxthandler.start)
