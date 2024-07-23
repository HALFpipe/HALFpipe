# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe

from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.make import MakeResultdicts
from ...utils.format import format_workflow

# from niworkflows.interfaces.plotting import ConfoundsCorrelationPlot


def init_setting_output_wf(workdir: str | None = None, setting_name: str | None = None):
    if setting_name is None:
        name = "setting_output_wf"
    else:
        name = f"setting_output_{format_workflow(setting_name)}_wf"
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["tags", "vals", "metadata", "bold", "confounds", "mask"]),
        name="inputnode",
    )

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(
            imagekeys=[
                "bold",
                "confounds_regressors",
                "brain_mask",
                "confoundcorr_bold",
            ]
        ),
        name="make_resultdicts",
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")
    workflow.connect(inputnode, "bold", make_resultdicts, "bold")
    workflow.connect(inputnode, "confounds", make_resultdicts, "confounds_regressors")
    workflow.connect(inputnode, "mask", make_resultdicts, "brain_mask")

    #
    resultdict_datasink = pe.Node(ResultdictDatasink(base_directory=workdir), name="resultdict_datasink")
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    # TODO fix this
    # conf_corr_plot = pe.Node(
    #     ConfoundsCorrelationPlot(reference_column="global_signal", max_dim=70),
    #     name="conf_corr_plot",
    # )
    # workflow.connect(inputnode, "confounds", conf_corr_plot, "confounds_file")
    #
    # #
    # workflow.connect(conf_corr_plot, "out_file", make_resultdicts, "confoundcorr_bold")

    return workflow
