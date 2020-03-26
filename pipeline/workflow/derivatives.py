# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

from nipype.pipeline import engine as pe
from nipype.interfaces import io as nio

from .utils import make_varname, dataSinkRegexpSubstitutions


def get_container_path(subject, scan=None, run=None):
    container = subject
    if scan is not None:
        container = op.join(container, scan)
        if run is not None:
            container = op.join(container, run)
    return container


def make_firstlevel_datasink(
    workflow,
    firstlevel_wf,
    outnames,
    outfields,
    output_dir,
    subject,
    scan=None,
    run=None,
):
    name = workflow.name

    varnames = []
    for outname in outnames:
        _outfields = outfields
        if isinstance(_outfields, dict):
            _outfields = _outfields[outname]
        for outfield in _outfields:
            varnames.append(make_varname(outname, outfield))

    ds_field = pe.Node(
        interface=nio.DataSink(
            infields=varnames,
            regexp_substitutions=dataSinkRegexpSubstitutions,
            parameterization=False,
            force_run=True,
        ),
        name="ds_{}".format(name),
        run_without_submitting=True,
    )
    ds_field.inputs.base_directory = output_dir
    ds_field.inputs.container = get_container_path(subject, scan, run)

    connections = []
    for varname in varnames:
        connections.append(
            (firstlevel_wf, ds_field, [("outputnode.{}".format(varname), varname)])
        )
    workflow.connect(connections)
