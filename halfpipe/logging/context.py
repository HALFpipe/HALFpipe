# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from multiprocessing import get_context
from threading import RLock

from .worker import run as runWorker, MessageSchema

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
                # wait for queue to empty
                cls.queue().join()

                # send message with teardown command
                obj = schema.dump({"type": "teardown"})
                cls.queue().put(obj)

                # wait up to one second
                cls.instance().worker.join(1.0)

    @classmethod
    def queue(cls):
        return cls.instance().queue

    @classmethod
    def loggingargs(cls):
        return dict(
            queue=cls.queue(),
            levelno=logging.getLogger("halfpipe").level
        )

    @classmethod
    def enableVerbose(cls):
        obj = schema.dump({"type": "enable_verbose"})
        cls.queue().put(obj)

    @classmethod
    def enablePrint(cls):
        obj = schema.dump({"type": "enable_print"})
        cls.queue().put(obj)
        cls.queue().join()

    @classmethod
    def disablePrint(cls):
        obj = schema.dump({"type": "disable_print"})
        cls.queue().put(obj)
        cls.queue().join()

    @classmethod
    def setWorkdir(cls, workdir):
        obj = schema.dump({"type": "set_workdir", "workdir": workdir})
        cls.queue().put(obj)

    def __init__(self):
        ctx = get_context("forkserver")

        self.queue = ctx.JoinableQueue()

        self.worker = ctx.Process(target=runWorker, args=(self.queue,))
        self.worker.start()
