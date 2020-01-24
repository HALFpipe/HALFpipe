# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op

from nipype.pipeline import engine as pe
from nipype.interfaces import io as nio


def get_container_path(subject, scan=None, run=None):
    container = subject
    if scan is not None:
        container = op.join(container, scan)
        if run is not None:
            container = op.join(container, run)
    return container


def make_firstlevel_datasink(workflow, 
                             firstlevel_wf, outnames, outfields,
                             output_dir, subject, scan=None, run=None):
    name = workflow.name

    for outname in outnames:
        for outfield in outfields:
            varname = "{}_{}".format(outname, outfield)

            ds_field = pe.Node(
                interface=nio.DataSink(
                    varname
                ),
                name="ds_{}_{}_{}".format(name, outname, outfield),
                run_without_submitting=True
            )
            ds_field.inputs.base_directory = output_dir
            ds_field.inputs.container = get_container_path(subject, scan, run)

            workflow.connect([
                (firstlevel_wf, ds_field, [
                    ("outputnode.{}".format(varname), varname)
                ]),
            ])
