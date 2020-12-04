# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import time

import stackprinter

fmt = "[{asctime},{msecs:04.0f}] [{name:16}] [{levelname:9}] {message}"
datefmt = "%Y-%m-%d %H:%M:%S"

black, red, green, yellow, blue, magenta, cyan, white = range(8)
resetseq = "\x1b[0m"
fillseq = "\x1b[K"
colorseq = "\x1b[{:d};{:d}m"
redseq = colorseq.format(30 + white, 40 + red)
yellowseq = colorseq.format(30 + black, 40 + yellow)
greenseq = colorseq.format(30 + white, 40 + green)
blueseq = colorseq.format(30 + white, 40 + blue)
greyseq = colorseq.format(30 + white, 100 + black)
colors = {
    "DEBUG": greyseq,
    "INFO": blueseq,
    "IMPORTANT": greenseq,
    "WARNING": yellowseq,
    "CRITICAL": redseq,
    "ERROR": redseq,
}


class Formatter(logging.Formatter):
    def __init__(self):
        super(Formatter, self).__init__(fmt=fmt, datefmt=datefmt, style="{")
        self.converter = time.localtime

    def formatException(self, exc_info):
        msg = stackprinter.format(exc_info)
        msg_indented = '    ' + '\n    '.join(msg.split('\n')).strip()
        return msg_indented

    def format(self, record):
        formatted = super(Formatter, self).format(record)

        lines = formatted.splitlines(True)

        lines = [line for line in lines if line.strip("\r\n\t ")]  # remove empty lines

        if len(lines) == 0 or len(lines) == 1:
            return formatted

        else:

            lines[0] = f"{lines[0]}"
            for i in range(1, len(lines) - 1):
                lines[i] = f"│ {lines[i]}"

            lines[-1] = f"└─{lines[-1]}"

            if lines[-1][-1] == "\n":
                lines[-1] = lines[-1][:-1]

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
