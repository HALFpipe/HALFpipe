# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from asyncio import get_event_loop

from .listener import listen


def run(queue):
    loop = get_event_loop()

    from halfpipe.logging import setup as setuplogging
    setuplogging(queue)

    try:
        loop.create_task(listen(queue))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
