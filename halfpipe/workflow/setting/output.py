# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu

from niworkflows.interfaces.plotting import ConfoundsCorrelationPlot

from ...interface import Select, Exec, MakeResultdicts, ResultdictDatasink
from ...utils import formatlikebids


def init_setting_output_wf(workdir=None, settingname=None):
    name = f"setting_output_{formatlikebids(settingname)}_wf"
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=["tags", "files", "mask"]), name="inputnode")

    #
    make_resultdicts = pe.Node(
        MakeResultdicts(
            imagekeys=["preproc_bold", "confounds_regressors", "brain_mask", "confoundcorr_bold"]
        ),
        name="make_resultdicts",
    )
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")

    workflow.connect(inputnode, "mask", make_resultdicts, "brain_mask")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    select = pe.Node(Select(regex=r".+\.tsv"), name="select", run_without_submitting=True)
    workflow.connect(inputnode, "files", select, "in_list")

    #
    unlistfiles = pe.Node(
        Exec(fieldtpls=[("bold", "firststr"), ("confounds", "firststr")]),
        name="unlistfiles",
        run_without_submitting=True,
    )  # discard any extra files, keep only first match
    workflow.connect(select, "match_list", unlistfiles, "confounds")
    workflow.connect(select, "other_list", unlistfiles, "bold")

    workflow.connect(unlistfiles, "bold", make_resultdicts, "preproc_bold")
    workflow.connect(unlistfiles, "confounds", make_resultdicts, "confounds_regressors")

    conf_corr_plot = pe.Node(
        ConfoundsCorrelationPlot(reference_column="global_signal", max_dim=70),
        name="conf_corr_plot",
    )
    workflow.connect(unlistfiles, "confounds", conf_corr_plot, "confounds_file")

    #
    workflow.connect(conf_corr_plot, "out_file", make_resultdicts, "confoundcorr_bold")

    return workflow
