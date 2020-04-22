# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op
import sys
import logging
import time

from filelock import SoftFileLock

from .io import IndexedFile


fmt = "[{asctime},{msecs:3.0f}] [{name:16}] [{levelname:7}] {message}"
datefmt = "%Y-%m-%d %H:%M:%S"

black, red, green, yellow, blue, magenta, cyan, white = range(8)
resetseq = "\x1b[0m"
fillseq = "\x1b[K"
colorseq = "\x1b[{:d};{:d}m"
redseq = colorseq.format(30 + white, 40 + red)
yellowseq = colorseq.format(30 + black, 40 + yellow)
blueseq = colorseq.format(30 + white, 40 + blue)
colors = {
    "DEBUG": blueseq,
    "INFO": blueseq,
    "WARNING": yellowseq,
    "CRITICAL": redseq,
    "ERROR": redseq,
}


class Formatter(logging.Formatter):
    def __init__(self):
        super(Formatter, self).__init__(fmt=fmt, datefmt=datefmt, style="{")
        self.converter = time.localtime

    def format(self, record):
        formatted = super(Formatter, self).format(record)
        lines = formatted.splitlines(True)
        if len(lines) == 0 or len(lines) == 1:
            return formatted
        else:
            line = lines[0]
            lines[0] = f"{line}"
            for i in range(1, len(lines) - 1):
                line = lines[i]
                lines[i] = f"│ {line}"
            line = lines[-1]
            lines[-1] = f"└─{line}"
            return "".join(lines)


class ColorFormatter(Formatter):
    def format(self, record):
        formatted = super(ColorFormatter, self).format(record)
        levelname = record.levelname
        if levelname in colors:
            color = colors[levelname]
            lines = formatted.splitlines(True)
            for i in range(len(lines)):
                line = lines[i]
                newlinechr = ""
                if line[-1] == "\n":
                    newlinechr = line[-1]
                    line = line[:-1]
                lines[i] = f"{color}{line}{fillseq}{resetseq}{newlinechr}"
            return "".join(lines)
        return formatted


class FileHandler(logging.FileHandler):
    def __init__(self, filename, **kwargs):
        super(FileHandler, self).__init__(filename, **kwargs)
        self.lock_file = f"{filename}.lock"
        self.stream_lock = SoftFileLock(self.lock_file)

    def acquire(self):
        logging.Handler.acquire(self)  # thread lock
        self.stream_lock.acquire()  # stream lock

    def release(self):
        try:
            self.stream_lock.release()  # stream lock
        finally:
            logging.Handler.release(self)  # thread lock


class JSReportHandler(logging.Handler):
    def __init__(self, filename, level=logging.INFO):
        super(JSReportHandler, self).__init__(level=level)
        self.filename = filename
        self.indexed_file_obj = None
        self.cur_nodename = None

    def emit(self, record):
        if self.indexed_file_obj is None and op.isfile(self.filename):
            try:
                self.indexed_file_obj = IndexedFile(self.filename)
            except Exception:
                pass

        nodeisdone = False
        nodestatus = None

        if record.msg == '[Node] Setting-up "%s" in "%s".':
            self.cur_nodename = record.args[0]
            nodestatus = "RUNNING"
        elif record.msg == '[Node] Cached "%s" - collecting precomputed outputs':
            pass
        elif record.msg == '[Node] "%s" found cached%s.':
            nodeisdone = True
            # nodestatus = "SUCCESS"
        elif record.msg.startswith("[Node] Running"):
            pass
        elif record.msg == '[Node] Finished "%s".':
            nodeisdone = True
            nodestatus = "SUCCESS"
        elif record.msg == "Node %s failed to run on host %s.":
            nodeisdone = True
            nodestatus = "FAILED"

        if (
            self.cur_nodename is not None
            and not self.cur_nodename.startswith("_")
            and nodestatus is not None
        ):
            if self.indexed_file_obj is None:
                logging.getLogger("pipeline").warning(
                    f"Missing indexed_file_obj to log nodestatus"
                )
            else:
                self.indexed_file_obj.set(self.cur_nodename, nodestatus)

        if nodeisdone:
            self.cur_nodename = None


def remove_handlers(logger):
    c = logger
    while c:
        for hdlr in c.handlers:
            c.removeHandler(hdlr)
        if not c.propagate:
            break
        else:
            c = c.parent


class Logger:
    is_setup = False

    def setup(workdir, debug=False, verbose=False):
        """
        Add new logging handler to nipype to output to log directory

        :param workdir: Log directory

        """
        Logger.is_setup = True

        import nipype  # noqa

        loggernames = [
            "pipeline",
            "pipeline.ui",
            "nipype",
            "nipype.workflow",
            "nipype.utils",
            "nipype.filemanip",
            "nipype.interface",
        ]

        for loggername in loggernames:
            logger = logging.getLogger(loggername)
            remove_handlers(logger)
            logger.propagate = False

        handlers = []

        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setFormatter(ColorFormatter())
        if debug:
            stdout_handler.setLevel(logging.DEBUG)
        elif verbose:
            stdout_handler.setLevel(logging.INFO)
        else:
            stdout_handler.setLevel(logging.WARNING)
        handlers.append(stdout_handler)

        formatter = Formatter()
        if workdir is not None:
            full_log_handler = FileHandler(op.join(workdir, "log.txt"))
            full_log_handler.setFormatter(formatter)
            if debug:
                full_log_handler.setLevel(logging.DEBUG)
            else:
                full_log_handler.setLevel(logging.INFO)
            handlers.append(full_log_handler)

            err_log_handler = FileHandler(op.join(workdir, "err.txt"))
            err_log_handler.setFormatter(formatter)
            err_log_handler.setLevel(logging.WARNING)
            handlers.append(err_log_handler)

        lowest_level = logging.INFO
        if debug:
            lowest_level = logging.DEBUG

        for loggername in loggernames:
            logger = logging.getLogger(loggername)
            logger.setLevel(lowest_level)
            for handler in handlers:
                logger.addHandler(handler)

        logging.getLogger("pipeline.ui").removeHandler(stdout_handler)  # only log to file

        logging.getLogger("nipype.workflow").addHandler(
            JSReportHandler(op.join(workdir, "report.js"))
        )
