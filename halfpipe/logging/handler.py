# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from logging import Handler

from .worker import MessageSchema

schema = MessageSchema()


class QueueHandler(Handler):
    def __init__(self, queue):
        super(QueueHandler, self).__init__()
        self.queue = queue

    def emit(self, record):
        try:
            msg = self.format(record)
            obj = schema.dump({"type": "log", "msg": msg, "levelno": record.levelno})
            self.queue.put(obj)
        except Exception:
            self.handleError(record)
