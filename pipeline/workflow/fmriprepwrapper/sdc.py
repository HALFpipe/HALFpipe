# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from sdcflows.workflows.pepolar import init_pepolar_unwarp_wf, check_pes
from sdcflows.workflows.fmap import init_fmap2field_wf, init_fmap_wf
from sdcflows.workflows.unwarp import init_sdc_unwarp_wf
from sdcflows.workflows.phdiff import init_phdiff_wf
from fmriprep import config

from ...io import canonicalize_pedir_str


def init_sdc_estimate_wf(fmap_type=None, name="sdc_estimate_wf"):
    """
    simplified from sdcflows/workflows/base.py
    """

    workflow = pe.Workflow(name=name if fmap_type else "sdc_bypass_wf")

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["epi_file", "epi_brain", "epi_mask", "metadata", "fmaps"]),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["epi_corrected", "epi_mask", "epi_brain", "out_warp", "method"]
        ),
        name="outputnode",
    )

    def get_phase_encoding_direction(dic):
        return dic.get("PhaseEncodingDirection")

    def get_magnitude(dic):
        return dic.get("magnitude")

    def get_fieldmap(dic):
        return dic.get("fieldmap")

    def get_phasediff(dic):
        return dic.get("phasediff")

    if fmap_type is None:
        outputnode.inputs.method = "None"
        workflow.connect(
            [
                (
                    inputnode,
                    outputnode,
                    [
                        ("epi_file", "epi_corrected"),
                        ("epi_mask", "epi_mask"),
                        ("epi_brain", "epi_brain"),
                    ],
                ),
            ]
        )
        return workflow
    elif fmap_type == "epi":
        matched_pe = True

        # Get EPI polarities and their metadata
        sdc_unwarp_wf = init_pepolar_unwarp_wf(
            matched_pe=matched_pe, omp_nthreads=config.nipype.omp_nthreads
        )

        workflow.connect(
            [
                (
                    inputnode,
                    sdc_unwarp_wf,
                    [
                        (("metadata", get_phase_encoding_direction,), "inputnode.epi_pe_dir",),
                        ("fmaps", "inputnode.fmaps_epi"),
                        ("epi_file", "inputnode.in_reference"),
                        ("epi_brain", "inputnode.in_reference_brain"),
                        ("epi_mask", "inputnode.in_mask"),
                    ],
                ),
            ]
        )
    elif fmap_type == "fieldmap" or fmap_type == "phasediff":
        if fmap_type == "fieldmap":
            outputnode.inputs.method = "FMB (fieldmap-based) - directly measured B0 map"
            fmap_wf = init_fmap_wf(omp_nthreads=config.nipype.omp_nthreads, fmap_bspline=False)
            workflow.connect(
                [
                    (
                        inputnode,
                        fmap_wf,
                        [
                            (("fmaps", get_magnitude), "inputnode.magnitude",),
                            (("fmaps", get_fieldmap), "inputnode.fieldmap",),
                        ],
                    )
                ]
            )
        elif fmap_type == "phasediff":
            outputnode.inputs.method = "FMB (fieldmap-based) - phase-difference map"
            fmap_wf = init_phdiff_wf(omp_nthreads=config.nipype.omp_nthreads)
            workflow.connect(
                [
                    (
                        inputnode,
                        fmap_wf,
                        [
                            (("fmaps", get_magnitude), "inputnode.magnitude",),
                            (("fmaps", get_phasediff), "inputnode.phasediff",),
                        ],
                    )
                ]
            )

        fmap2field_wf = init_fmap2field_wf(
            omp_nthreads=config.nipype.omp_nthreads, debug=config.execution.debug
        )
        workflow.connect(
            [
                (
                    inputnode,
                    fmap2field_wf,
                    [
                        ("epi_file", "inputnode.in_reference"),
                        ("epi_brain", "inputnode.in_reference_brain"),
                        ("metadata", "inputnode.metadata"),
                    ],
                ),
                (
                    fmap_wf,
                    fmap2field_wf,
                    [
                        ("outputnode.fmap", "inputnode.fmap"),
                        ("outputnode.fmap_ref", "inputnode.fmap_ref"),
                        ("outputnode.fmap_mask", "inputnode.fmap_mask"),
                    ],
                ),
            ]
        )

        sdc_unwarp_wf = init_sdc_unwarp_wf(
            omp_nthreads=config.nipype.omp_nthreads,
            debug=config.execution.debug,
            name="sdc_unwarp_wf",
        )
        workflow.connect(
            [
                (
                    inputnode,
                    sdc_unwarp_wf,
                    [
                        ("epi_file", "inputnode.in_reference"),
                        ("epi_mask", "inputnode.in_reference_mask"),
                    ],
                ),
                (fmap2field_wf, sdc_unwarp_wf, [("outputnode.out_warp", "inputnode.in_warp")],),
            ]
        )
    else:
        raise ValueError(f"Fieldmaps of type {fmap_type} are not supported")

    workflow.connect(
        [
            (
                sdc_unwarp_wf,
                outputnode,
                [
                    ("outputnode.out_warp", "out_warp"),
                    ("outputnode.out_reference", "epi_corrected"),
                    ("outputnode.out_reference_brain", "epi_brain"),
                    ("outputnode.out_mask", "epi_mask"),
                ],
            ),
        ]
    )

    return workflow


# Utility functions
def get_fmaps(boldfile, database):
    fmapfiles = database.get_associations(boldfile, datatype="fmap")

    pedir_str = database.get_tagval(boldfile, "phase_encoding_direction")
    if pedir_str is None:
        return None, None, {}
    pedir_str = canonicalize_pedir_str(pedir_str, boldfile)
    metadata = {
        "PhaseEncodingDirection": pedir_str,
    }

    epi = []
    magnitude = []
    phasediff = []
    fieldmap = []
    for fmapfile in fmapfiles:
        suffix = database.get_tagval(fmapfile, "suffix")
        if suffix.startswith("phase"):
            phasediff.append(fmapfile)
        elif suffix.startswith("magnitude"):
            magnitude.append(fmapfile)
        elif suffix == "fieldmap":
            fieldmap.append(fmapfile)
        elif suffix == "epi":
            epi.append(fmapfile)

    if len(epi) > 0:
        try:
            matched_pe = check_pes(epi)
            if matched_pe:
                metadata["fmap_type"] = "epi"
                return "epi", epi, metadata
        except ValueError as ve:
            logging.getLogger("pipeline").warn(f"Skip fmap: %s", ve, stack_info=True)

    if len(magnitude) > 0:
        ees = database.get_tagval(boldfile, "effective_echo_spacing")
        if ees is None:
            logging.getLogger("pipeline").warn(
                f"Skip fmap: effective_echo_spacing not found for {boldfile}"
            )
            return None, None, metadata
        metadata["EffectiveEchoSpacing"] = ees
        if len(fieldmap) > 0:
            fmaps = {"magnitude": magnitude.pop(), "fieldmap": fieldmap.pop()}
            metadata["fmap_type"] = "fieldmap"
            return "fieldmap", fmaps, metadata

        if len(phasediff) > 0:
            if len(phasediff) == 1:
                (fmapfile,) = phasediff
                etd = database.get_tagval(fmapfile, "echo_time_difference")
                if etd is None:
                    logging.getLogger("pipeline").warn(
                        f"Skip fmap: echo_time_difference not found for {fmapfile}"
                    )
                    return None, None, metadata
                fmaps = {
                    "magnitude": magnitude.pop(),
                    "phasediff": [(fmapfile, {"EchoTimeDifference": etd})],
                }
            elif len(phasediff) == 2:
                fmaps = {
                    "magnitude": magnitude.pop(),
                    "phasediff": [],
                }
                for fmapfile in phasediff:
                    et = database.get_tagval(fmapfile, "echo_time")
                    if et is None:
                        logging.getLogger("pipeline").warn(
                            f"Skip fmap: echo_time not found for {fmapfile}"
                        )
                        return None, None, metadata
                    fmaps["phasediff"].append([(fmapfile, {"EchoTime": et})])
            else:
                nphasediff = len(phasediff)
                logging.getLogger("pipeline").warn(
                    f"Skip fmap: invalid number of phase images ({nphasediff})"
                )
                return None, None, metadata
            metadata["fmap_type"] = "phasediff"
            return "phasediff", fmaps, metadata

    metadata["fmap_type"] = "none"
    return None, None, metadata
