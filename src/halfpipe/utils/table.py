# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import logging
from pathlib import Path
from types import TracebackType
from typing import Any, Self, Type

import numpy as np
import pandas as pd
from tabulate import tabulate

from ..model.tags import entities
from .json import TypeAwareJSONEncoder
from .lock import AdaptiveLock
from .ops import check_almost_equal


class SynchronizedTable:
    def __init__(
        self,
        filename: Path | str,
        header: str | None = "report('",
        footer: str | None = "');",
    ) -> None:
        self.filename = Path(filename)
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        self.lockfilename = f"{filename}.lock"
        self.lock = AdaptiveLock()

        self.header_bytes = None
        if isinstance(header, str):
            self.header_bytes = header.encode()
        self.footer_bytes = None
        if isinstance(footer, str):
            self.footer_bytes = footer.encode()

        self.dictlist: list[dict] | None = None
        self.is_dirty: bool | None = None

    def load(self) -> None:
        if self.filename.is_file():
            with open(str(self.filename), "rb") as fp:
                bytesfromfile = fp.read()
            try:
                if self.header_bytes is not None:
                    bytesfromfile = bytesfromfile[len(self.header_bytes) :]
                if self.footer_bytes is not None:
                    bytesfromfile = bytesfromfile[: -len(self.footer_bytes)]
                jsonstr = bytesfromfile.decode()
                jsonstr = jsonstr.replace("\\\n", "")
                self.dictlist = json.loads(jsonstr)
            except json.decoder.JSONDecodeError as e:
                logging.warning("JSONDecodeError %s", e)
        if self.dictlist is None:
            self.dictlist = list()

    def dump(self, opener=open, mode="wb") -> None:
        with opener(str(self.filename), mode) as file_handle:
            file_handle.write(self.header_bytes)
            jsonstr = json.dumps(
                self.dictlist,
                indent=4,
                sort_keys=True,
                ensure_ascii=False,
                cls=TypeAwareJSONEncoder,
            )
            for line in jsonstr.splitlines():
                file_handle.write(line.encode())
                file_handle.write("\\\n".encode())
            file_handle.write(self.footer_bytes)

    def __enter__(self) -> Self:
        self.lock.lock(self.lockfilename)

        self.is_dirty = False
        self.load()

        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.is_dirty:
            self.dump()
        try:
            self.lock.unlock()
        except RuntimeError:
            pass
        self.dictlist = None

    def to_table(self) -> None:
        assert self.dictlist is not None

        dictlist = [{str(k): str(v) for k, v in indict.items()} for indict in self.dictlist]
        data_frame = pd.DataFrame.from_records(dictlist)
        assert isinstance(data_frame, pd.DataFrame)

        data_frame.replace({np.nan: ""}, inplace=True)

        columns = list(map(str, data_frame.columns))
        columns_in_order = [entity for entity in reversed(entities) if entity in columns]
        columns_in_order.extend(sorted([column for column in columns if column not in entities]))

        data_frame = data_frame[columns_in_order]
        assert isinstance(data_frame, pd.DataFrame)

        table_str = tabulate(
            data_frame,  # type: ignore
            headers="keys",
            showindex=False,
            disable_numparse=True,
        )

        table_filename = self.filename.parent / f"{self.filename.stem}.txt"
        with open(str(table_filename), "w") as fp:
            fp.write(table_str)
            fp.write("\n")

    def put(self, indict: dict[str, Any]) -> None:
        assert self.dictlist is not None

        intags = {k: v for k, v in indict.items() if k in entities}

        matches = False

        for i in range(len(self.dictlist)):
            curdict = self.dictlist[i]

            curtags = {k: v for k, v in curdict.items() if k in entities}

            if set(intags.items()) == set(curtags.items()):
                if set(indict.keys()) == set(curdict.keys()):
                    if check_almost_equal(indict, curdict):
                        return  # update not needed

                matches = True

                self.dictlist[i].update(indict)
                logging.debug(f"Updating {self.filename} entry {curdict} with {indict}")

                break

        if not matches:
            self.dictlist.append(indict)

        self.is_dirty = True  # will need to write out file
