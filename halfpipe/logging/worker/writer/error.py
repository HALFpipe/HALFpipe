# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re

from .file import FileWriter, escape_codes_regex
from ....io import DictListFile


could_not_run_match = re.compile(r"could not run node: (?P<fullname>nipype\.[^\s]+)").search
crash_info_match = re.compile(r"Saving crash info to (?P<crash_file_path>.+)").search
crash_file_match = re.compile(r"Node: (?P<fullname>nipype\.[^\s]+)").match


class ReportErrorWriter(FileWriter):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.dictlistfile = None

    def filterMessage(self, message):
        msg = message.msg
        msg = escape_codes_regex.sub("", msg)

        match = could_not_run_match(msg)
        if match is not None:
            message.node = match.group("fullname")
            return True

        match = crash_info_match(msg)
        if match is not None:
            crash_file_path = match.group("crash_file_path")
            with open(crash_file_path, "r") as crash_file_handle:
                crash_file_str = crash_file_handle.read()
            match = crash_file_match(crash_file_str)
            if match is not None:
                message.node = match.group("fullname")
                return True

        return False

    def acquire(self):
        if self.dictlistfile is None:
            self.dictlistfile = DictListFile.cached(self.filename)

        self.dictlistfile.__enter__()

    def emitmessage(self, message):
        self.dictlistfile.put(dict(
            node=message.node
        ))

    def release(self):
        self.dictlistfile.__exit__()
