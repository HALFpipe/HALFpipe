# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

dataSinkRegexpSubstitutions = [
    (r"^(/.+)/dof$", r"\1"),
    (r"^(/.+)/.+.txt$", r"\1.txt"),
    (r"^(/.+)/.+.nii.gz$", r"\1.nii.gz"),
    (r"trait_added$", r""),
    (r"suffix$", r""),
]


def make_varname(outname, outfield):
    return "{}_{}".format(outname, outfield)


def make_outputnode(workflow, outByWorkflowName,
                    extraOutfields=[], extraVarnames=[]):
    # get outputnode field names
    varnames = []
    for workflowName, (firstlevel_wf, outnames, outfields) \
            in outByWorkflowName.items():
        for outname in outnames:
            _outfields = outfields
            if isinstance(_outfields, dict):
                _outfields = _outfields[outname]
            for outfield in _outfields:
                varnames.append(make_varname(outname, outfield))
            for outfield in extraOutfields:
                varnames.append(make_varname(outname, outfield))

    varnames.extend(extraVarnames)

    if len(varnames) == 0:
        return None, {}

    outputnode = pe.Node(
        interface=niu.IdentityInterface(
            fields=varnames
        ),
        name="outputnode"
    )

    # connect outputs
    for workflowName, (wf, outnames, outfields) \
            in outByWorkflowName.items():
        for outname in outnames:
            _outfields = outfields
            if isinstance(_outfields, dict):
                _outfields = _outfields[outname]
            for outfield in _outfields:
                varname = make_varname(outname, outfield)
                workflow.connect([
                    (wf, outputnode, [
                        ("outputnode.{}".format(varname), varname)
                    ])
                ])

    # make spec
    outfieldsByOutname = {
        outname:
            outfields if isinstance(outfields, list) else outfields[outname]
        for workflowName, (_, outnames, outfields) in outByWorkflowName.items()
        for outname in outnames
    }

    for outfield in extraOutfields:
        for outname in outfieldsByOutname.keys():
            outfieldsByOutname[outname].append(outfield)

    return outputnode, outfieldsByOutname
