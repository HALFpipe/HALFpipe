# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from asyncio import get_event_loop

from multiprocessing import Process

from .listener import listen


class Worker(Process):
    def __init__(self, queue):
        super(Worker, self).__init__()

        self.queue = queue

    def run(self):
        loop = get_event_loop()

        try:
            loop.create_task(listen(self.queue))
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
