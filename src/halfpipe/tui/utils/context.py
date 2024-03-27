# -*- coding: utf-8 -*-
# from .ui.components import SingleChoiceInputView, SpacerView, TextElement, TextView
from pathlib import Path

from ...ingest.database import Database

# from ..logging import logger
from ...model.spec import Spec, SpecSchema


class Context:
    def __init__(self) -> None:
        spec_schema = SpecSchema()
        spec = spec_schema.load(spec_schema.dump({}), partial=True)
        assert isinstance(spec, Spec)
        self.spec: Spec = spec  # initialize with defaults
        self.database = Database(self.spec)
        self.workdir: Path | None = None
        self.use_existing_spec = False
        self.debug = False
        self.already_checked: set[str] = set()

    def put(self, fileobj):
        self.database.put(fileobj)
        return len(self.spec.files) - 1
