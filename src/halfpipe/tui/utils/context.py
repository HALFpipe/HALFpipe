# -*- coding: utf-8 -*-
# from .ui.components import SingleChoiceInputView, SpacerView, TextElement, TextView
from collections import defaultdict
from pathlib import Path
from typing import Any

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

# from ..logging import logger
from ...model.spec import Spec, SpecSchema
from ...model.tags import entities


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
        self.cache: defaultdict[str, defaultdict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
        self.available_images: dict = {}

    def put(self, fileobj):
        self.database.put(fileobj)
        return len(self.spec.files) - 1

    def refresh_available_images(self):
        bold_filedict = {"datatype": "func", "suffix": "bold"}
        filepaths = self.database.get(**bold_filedict)

        db_entities, db_tags_set = self.database.multitagvalset(entities, filepaths=filepaths)
        self.available_images[db_entities[0]] = sorted(list({t[0] for t in db_tags_set}))

    @property
    def get_available_images(self):
        return self.available_images


ctx = Context()
