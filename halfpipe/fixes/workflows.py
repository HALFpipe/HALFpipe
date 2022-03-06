# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path
from uuid import UUID

from nipype.pipeline import engine as pe


class IdentifiableWorkflow(pe.Workflow):
    def __init__(self, name, base_dir: Path, uuid: UUID | None = None):
        super(IdentifiableWorkflow, self).__init__(name, base_dir=base_dir)

        self.uuid = uuid
        self.bids_to_sub_id_map: dict[str, str] = dict()
