# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from mriqc import config
from mriqc.workflows.core import init_mriqc_wf

from .factory import Factory
from .constants import constants


class MriqcFactory(Factory):
    def __init__(self, ctx):
        super(MriqcFactory, self).__init__(ctx)

    def setup(self, workdir, boldfilepaths):
        database = self.database
        bidsdatabase = self.bidsdatabase
        workflow = self.workflow
        uuidstr = str(workflow.uuid)[:8]
        bids_dir = Path(workdir) / "rawdata"

        # init mriqc config
        output_dir = Path(workdir) / "derivatives"
        output_dir.mkdir(parents=True, exist_ok=True)

        subjects = set()
        bidssubjects = set()
        for boldfilepath in boldfilepaths:
            subjects.add(database.tagval(boldfilepath, "sub"))
            bidspath = bidsdatabase.tobids(boldfilepath)
            bidssubjects.add(bidsdatabase.tagval(bidspath, "subject"))
        subjects = list(subjects)
        bidssubjects = list(bidssubjects)

        config.from_dict(
            {
                "bids_dir": bids_dir,
                "output_dir": output_dir,
                "log_dir": workdir,
                "participant_label": bidssubjects,
                "analysis_level": ["participant", "group"]
            }
        )
        nipype_dir = Path(workdir) / constants.workflowdir
        nipype_dir.mkdir(parents=True, exist_ok=True)
        config_file = nipype_dir / f"mriqc.config.{uuidstr}.toml"
        config.to_filename(config_file)

        mriqc_wf = init_mriqc_wf()
        workflow.add_nodes([mriqc_wf])

    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def connect(self, nodehierarchy, node, *args, **kwargs):
        return super().connect(nodehierarchy, node, *args, **kwargs)
