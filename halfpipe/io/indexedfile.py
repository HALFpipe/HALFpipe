# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from functools import lru_cache
import logging
from pathlib import Path

from ..utils import loadpicklelzma, savepicklelzma


def _quote(val, maxlen, append_comma):
    val = val[:maxlen]
    quoted = f'"{val}"'
    desiredlen = maxlen + 2
    if append_comma:
        quoted += ","
        desiredlen += 1
    return f"{quoted:{desiredlen}}"


class FileIndex:
    def __init__(self, indexdict, maxlen, append_comma, lastkey=None):
        self.indexdict = indexdict
        self.maxlen = maxlen
        self.append_comma = append_comma
        self.lastkey = lastkey


class IndexedFile:
    def __init__(self, filename):
        self.filename = filename
        assert Path(filename).is_file()
        self.lock_file = f"{filename}.lock"
        index_file = f"{filename}.index.pickle.xz"
        self.file_index = _load_index_file(index_file)
        assert isinstance(self.file_index, FileIndex)

    def set(self, key, value):
        if key not in self.file_index.indexdict:
            logging.getLogger("halfpipe").warning(
                f'Key "{key}" not found for IndexedFile "{self.filename}"'
            )
            return
        if not isinstance(value, str):
            return
        append_comma = self.file_index.append_comma
        if append_comma is True and key == self.file_index.lastkey:
            append_comma = False
        with open(self.filename, "r+b") as fp:
            fp.seek(self.file_index.indexdict[key])
            padded = _quote(value, self.file_index.maxlen, append_comma).encode()
            fp.write(padded)


@lru_cache(maxsize=128)
def _load_index_file(filename):
    return loadpicklelzma(filename)


def init_indexed_js_object_file(filename, functionname, keynames, maxlen, defaultvalue=""):
    append_comma = True
    indexdict = dict()
    lastkey = None
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as fp:
        fp.write(f"{functionname}('{{ ".encode())
        fp.write("\\\n".encode())
        placeholder = _quote(defaultvalue, maxlen, append_comma).encode()
        for i, keyname in enumerate(keynames):
            if i == len(keynames) - 1:  # last iteration
                placeholder = _quote(defaultvalue, maxlen, False).encode()
                lastkey = keyname
            fp.write(f'  "{keyname}": '.encode())
            indexdict[keyname] = fp.tell()
            fp.write(placeholder)
            fp.write(" \\\n".encode())
        fp.write("}');\n".encode())
    index_file = f"{filename}.index.pickle.xz"
    index = FileIndex(indexdict, maxlen, append_comma, lastkey=lastkey)
    savepicklelzma(index_file, index)


def init_indexed_js_list_file(
    filename, functionname, keytupls_list, maxlen, valuekeyname="value", defaultvalue=""
):
    append_comma = False
    indexdict = dict()
    with open(filename, "wb") as fp:
        fp.write(f"{functionname}('[ ".encode())
        fp.write("\\\n".encode())
        placeholder = _quote(defaultvalue, maxlen, append_comma).encode()
        first = True
        for keytupls in keytupls_list:
            if not first:
                fp.write(", \\\n".encode())
            first = False
            fp.write("  { \\\n".encode())
            for key, val in keytupls:
                fp.write(f'    "{key}": "{val}", \\\n'.encode())
            fp.write(f'    "{valuekeyname}": '.encode())
            indexdict[keytupls] = fp.tell()
            fp.write(placeholder)
            fp.write(f" \\\n".encode())
            fp.write("  }".encode())
        fp.write(" \\\n]');\n".encode())
    index_file = f"{filename}.index.pickle.xz"
    index = FileIndex(indexdict, maxlen, append_comma)
    savepicklelzma(index_file, index)
