# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
import logging
import json
from functools import lru_cache

import pandas as pd
import numpy as np

import fasteners
from tabulate import tabulate

from ...model import entities

logger = logging.getLogger("halfpipe")


class DictListFile:
    def __init__(self, filename, header="report('", footer="');"):
        self.filename = Path(filename)
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        lockfilename = f"{filename}.lock"
        self.lock = fasteners.InterProcessLock(str(lockfilename))

        if isinstance(header, str):
            header = header.encode()
        self.header = header

        if isinstance(footer, str):
            footer = footer.encode()
        self.footer = footer

        self.dictlist = None
        self.is_dirty = None

    @classmethod
    @lru_cache(maxsize=128)
    def cached(cls, filename, **kwargs):
        return cls(filename, **kwargs)

    def __enter__(self):
        self.lock.acquire()

        self.dictlist = []
        self.is_dirty = False
        if self.filename.is_file():
            with open(str(self.filename), "rb") as fp:
                bytesfromfile = fp.read()
            try:
                if self.header is not None:
                    bytesfromfile = bytesfromfile[len(self.header) :]
                if self.footer is not None:
                    bytesfromfile = bytesfromfile[: -len(self.footer)]
                jsonstr = bytesfromfile.decode()
                jsonstr = jsonstr.replace("\\\n", "")
                self.dictlist = json.loads(jsonstr)
            except json.decoder.JSONDecodeError as e:
                logging.getLogger("halfpipe").warning("JSONDecodeError %s", e)

    def __exit__(self, *args):
        if self.is_dirty:
            with open(str(self.filename), "w") as fp:
                fp.write(self.header.decode())
                jsonstr = json.dumps(self.dictlist, indent=4, ensure_ascii=False)
                for line in jsonstr.splitlines():
                    fp.write(line)
                    fp.write("\\\n")
                fp.write(self.footer.decode())
        try:
            self.lock.release()
        except RuntimeError:
            pass
        self.dictlist = None

    def to_table(self):
        dictlist = [{str(k): str(v) for k, v in indict.items()} for indict in self.dictlist]
        dataframe = pd.DataFrame.from_records(dictlist)
        dataframe = dataframe.replace({np.nan: ""})

        columnsinorder = [entity for entity in reversed(entities) if entity in dataframe]
        columnsinorder.extend(sorted([column for column in dataframe if column not in entities]))

        dataframe = dataframe[columnsinorder]

        table_str = tabulate(dataframe, headers="keys", showindex=False)

        table_filename = self.filename.parent / f"{self.filename.stem}.txt"
        with open(str(table_filename), "w") as fp:
            fp.write(table_str)
            fp.write("\n")

    def put(self, indict):
        assert self.dictlist is not None

        matches = False

        for i, curdict in enumerate(self.dictlist):
            matches = True
            equals = True
            for key, value in curdict.items():
                def _compare(a, b):
                    if isinstance(a, float) and isinstance(b, float):
                        return np.isclose(a, b)
                    return a == b
                valmatches = key in indict and _compare(indict[key], curdict[key])
                if key in entities:
                    matches = matches and valmatches
                equals = equals and valmatches
            if equals:
                return
            if matches:
                break
        self.is_dirty = True
        if matches:
            self.dictlist[i].update(indict)
            logger.debug(f"Updating {self.filename} entry {curdict} with {indict}")
        else:
            self.dictlist.append(indict)
