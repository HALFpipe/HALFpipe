# -*- coding: utf-8 -*-
# from .ui.components import SingleChoiceInputView, SpacerView, TextElement, TextView
from collections import defaultdict
from pathlib import Path
from typing import Any, Union

# class Context:
# def __init__(self) -> None:
# spec_schema = SpecSchema()
# spec = spec_schema.load(spec_schema.dump({}), partial=True)
# assert isinstance(spec, Spec)
# self.spec: Spec = spec  # initialize with defaults
# self.database = Database(self.spec)
# self.workdir: Path | None = None
# self.use_existing_spec = False
# self.debug = False
# self.already_checked: set[str] = set()
# def put(self, fileobj):
# self.database.put(fileobj)
# return len(self.spec.files) - 1
from ...ingest.database import Database
from ...model.file.base import File

# from ..logging import logger
from ...model.spec import Spec, SpecSchema


# singleton
class Context:
    _instance = None
    _initialized: bool

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Context, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        spec_schema = SpecSchema()
        spec = spec_schema.load(spec_schema.dump({}), partial=True)
        assert isinstance(spec, Spec)
        self.spec: Spec = spec  # initialize with defaults
        self.database = Database(self.spec)
        self.workdir: Path | None = None
        self.use_existing_spec = False
        self.debug = False
        self.already_checked: set[str] = set()
        self._initialized = True
        self.cache: defaultdict[str, defaultdict[str, Union[dict[str, Any], File]]] = defaultdict(lambda: defaultdict(dict))

    def put(self, fileobj):
        self.database.put(fileobj)
        return len(self.spec.files) - 1


ctx = Context()
