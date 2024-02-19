# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import curses
import threading
from queue import SimpleQueue
from time import sleep

from .color import Color
from .cursor import Cursor
from .keyboard import Keyboard

frame_delay_seconds = 50.0 / 1000.0  # 20 fps


class App:
    def __init__(self):
        self.should_quit = False

        self.queue: SimpleQueue = SimpleQueue()
        self.condition = threading.Condition()
        self.thread = threading.Thread(target=self.main)

        self.color: Color | None = None
        self.keyboard: Keyboard | None = None

    def __enter__(self):
        with self.condition:
            self.thread.start()
            self.condition.wait()

    def __exit__(self, type, value, tb):
        self.should_quit = True
        self.thread.join()

    def dispatch(self, func):
        self.queue.put_nowait(func)

    def main(self):
        _error = None
        try:
            self.setup()
            with self.condition:
                self.condition.notify_all()
            while not self.should_quit:
                self.loop()
                sleep(frame_delay_seconds)
        except Exception as e:
            _error = e
        finally:
            self.cleanup()

        if _error:
            raise _error

    def setup(self):
        from .layout import Layout

        self.screen = curses.initscr()

        curses.start_color()
        curses.use_default_colors()

        curses.raw()
        curses.noecho()
        self.screen.nodelay(True)
        self.screen.keypad(True)
        Cursor.hide()

        self.color = Color()
        self.keyboard = Keyboard()
        self.layout = Layout(self)
        self.is_dirty = False

    def cleanup(self):
        Cursor.show()
        self.screen.keypad(False)
        self.screen.nodelay(False)
        curses.noraw()
        curses.echo()
        curses.endwin()

    def loop(self):
        while True:
            c = self.screen.getch()
            if c == -1:  # no character available
                break
            if c == curses.KEY_RESIZE:  # resize
                self.is_dirty = True
            elif self.keyboard is not None:
                self.keyboard(c)

        while not self.queue.empty():
            func = self.queue.get_nowait()
            assert func is not None and callable(func)
            func()
            self.is_dirty = True

        if self.is_dirty:
            self.layout.draw()
            self.is_dirty = False
