# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from ..confounds import init_confoundsregression_wf
from ..temporalfilter import init_bandpass_wf
from .brainatlas import init_brainatlas_wf
from .seedconnectivity import init_seedconnectivity_wf
from .dualregression import init_dualregression_wf
from .reho import init_reho_wf
from .alff import init_alff_wf

from ..memory import MemoryCalculator

from ..utils import make_outputnode


def init_rest_wf(metadata,
                 name="rest",
                 memcalc=MemoryCalculator()):

    workflow = pe.Workflow(name=name)

    # inputs are the bold file, the mask file and the confounds file
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file_d",
                "confounds_d",
                "bold_file_df",
                "confounds_df",
                "bold_file_sdf",
                "confounds_sdf",
                "mask_file"]),
        name="inputnode"
    )

    unfilteredFileEndpointd = [inputnode, "bold_file_d"]
    confoundsFilteredFileEndpointd = unfilteredFileEndpointd
    confoundsregressiond = init_confoundsregression_wf(metadata)
    if confoundsregressiond is not None:
        workflow.connect(
            *unfilteredFileEndpointd,
            confoundsregressiond, "inputnode.bold_file"
        )
        workflow.connect([
            (inputnode, confoundsregressiond, [
                ("confounds_d", "inputnode.confounds"),
                ("mask_file", "inputnode.mask_file"),
            ])
        ])
        confoundsFilteredFileEndpointd = \
            [confoundsregressiond, "outputnode.filtered_file"]

    repetition_time = metadata["RepetitionTime"]

    bandpass_wf = init_bandpass_wf(repetition_time)
    workflow.connect(
        *confoundsFilteredFileEndpointd,
        bandpass_wf, "inputnode.bold_file"
    )
    bandpassFilteredFileEndpointd = [bandpass_wf, "outputnode.filtered_file"]

    workflow.connect([
        (inputnode, bandpass_wf, [
            ("mask_file", "inputnode.mask_file"),
        ])
    ])

    outByWorkflowName = {}

    def aggregate(out):
        wf, outnames, outfields = out

        if len(outnames) == 0:
            return

        outByWorkflowName[wf.name] = out

    out = init_brainatlas_wf(metadata, memcalc=memcalc)
    aggregate(out)
    brainatlas_wf, outnames, _ = out
    if len(outnames) > 0:
        unfilteredFileEndpointdf = [inputnode, "bold_file_df"]
        confoundsFilteredFileEndpointdf = unfilteredFileEndpointdf
        confoundsregressiondf = init_confoundsregression_wf(metadata)
        if confoundsregressiondf is not None:
            workflow.connect(
                *unfilteredFileEndpointdf,
                confoundsregressiondf, "inputnode.bold_file"
            )
            workflow.connect([
                (inputnode, confoundsregressiondf, [
                    ("confounds_d", "inputnode.confounds"),
                    ("mask_file", "inputnode.mask_file"),
                ])
            ])
            confoundsFilteredFileEndpointdf = \
                [confoundsregressiond, "outputnode.filtered_file"]
        workflow.connect(
            *confoundsFilteredFileEndpointdf,
            brainatlas_wf, "inputnode.bold_file"
        )

    out = init_seedconnectivity_wf(metadata, memcalc=memcalc)
    aggregate(out)
    seedconnectivity_wf, outnames, _ = out
    if len(outnames) > 0:
        workflow.connect([
            (inputnode, seedconnectivity_wf, [
                ("bold_file_sdf", "inputnode.bold_file"),
                ("confounds_sdf", "inputnode.confounds")
            ])
        ])

    if "ICAMaps" in metadata:
        for name, componentsfile in metadata["ICAMaps"].items():
            out = init_dualregression_wf(
                metadata,
                componentsfile,
                name="{}_dualregression_wf".format(name),
                memcalc=memcalc
            )
            aggregate(out)
            dualregression_wf, outnames, _ = out
            if len(outnames) > 0:
                workflow.connect([
                    (inputnode, dualregression_wf, [
                        ("bold_file_sdf", "inputnode.bold_file"),
                        ("confounds_sdf", "inputnode.confounds")
                    ])
                ])

    if "ReHo" in metadata and metadata["ReHo"]:
        out = init_reho_wf(memcalc=memcalc)
        aggregate(out)
        reho_wf, outnames, _ = out
        if len(outnames) > 0:
            workflow.connect(
                *bandpassFilteredFileEndpointd,
                reho_wf, "inputnode.bold_file"
            )

    if "ALFF" in metadata and metadata["ALFF"]:
        out = init_alff_wf(memcalc=memcalc)
        aggregate(out)
        alff_wf, outnames, _ = out
        if len(outnames) > 0:
            workflow.connect(
                *confoundsFilteredFileEndpointd,
                alff_wf, "inputnode.bold_file"
            )
            workflow.connect(
                *bandpassFilteredFileEndpointd,
                alff_wf, "inputnode.filtered_file"
            )

    for workflowName, (wf, outnames, outfields) in outByWorkflowName.items():
        workflow.connect([
            (inputnode, wf, [
                ("mask_file", "inputnode.mask_file")
            ])
        ])

    _, outfieldsByOutname = make_outputnode(
        workflow, outByWorkflowName
    )

    outnames = list(outfieldsByOutname.keys())

    return workflow, outnames, outfieldsByOutname
