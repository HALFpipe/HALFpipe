# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
import json
from functools import lru_cache
from math import isclose

import pandas as pd
import numpy as np
from tabulate import tabulate

from .lock import AdaptiveLock
from ...model.tags import entities
from ...utils import logger


def _compare(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return isclose(a, b)
    else:
        return a == b


class DictListFile:
    def __init__(self, filename, header="report('", footer="');"):
        self.filename = Path(filename)
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        self.lockfilename = f"{filename}.lock"
        self.lock = AdaptiveLock()

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
        self.lock.lock(self.lockfilename)

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
                logger.warning("JSONDecodeError %s", e)
        return self

    def __exit__(self, *args):
        if self.is_dirty:
            with open(str(self.filename), "w") as fp:
                fp.write(self.header.decode())
                jsonstr = json.dumps(self.dictlist, indent=4, sort_keys=True, ensure_ascii=False)
                for line in jsonstr.splitlines():
                    fp.write(line)
                    fp.write("\\\n")
                fp.write(self.footer.decode())
        try:
            self.lock.unlock()
        except RuntimeError:
            pass
        self.dictlist = None

    def to_table(self):
        dictlist = [{str(k): str(v) for k, v in indict.items()} for indict in self.dictlist]
        dataframe = pd.DataFrame.from_records(dictlist)
        dataframe = dataframe.replace({np.nan: ""})

        columns = list(map(str, dataframe.columns))
        columnsinorder = [entity for entity in reversed(entities) if entity in columns]
        columnsinorder.extend(sorted([column for column in columns if column not in entities]))

        dataframe = dataframe[columnsinorder]

        table_str = tabulate(dataframe, headers="keys", showindex=False)  # type: ignore

        table_filename = self.filename.parent / f"{self.filename.stem}.txt"
        with open(str(table_filename), "w") as fp:
            fp.write(table_str)
            fp.write("\n")

    def put(self, indict):
        assert self.dictlist is not None

        intags = {
            k: v for k, v in indict.items() if k in entities
        }

        matches = False

        for i in range(len(self.dictlist)):
            curdict = self.dictlist[i]

            curtags = {
                k: v for k, v in curdict.items() if k in entities
            }

            if set(intags.items()) == set(curtags.items()):
                if set(indict.keys()) == set(curdict.keys()):
                    if all(_compare(v, curdict[k]) for k, v in indict.items()):
                        return  # update not needed

                matches = True

                self.dictlist[i].update(indict)
                logger.debug(f"Updating {self.filename} entry {curdict} with {indict}")

                break

        if not matches:
            self.dictlist.append(indict)

        self.is_dirty = True  # will need to write out file
