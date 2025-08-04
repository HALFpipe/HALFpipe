# -*- coding: utf-8 -*-
import os
from math import isfinite
from pathlib import Path

import nipype.algorithms.modelgen as model
import nipype.interfaces.utility as niu
import numpy as np
from nipype.interfaces.fsl import FILMGLS, FEATModel, Merge
from nipype.interfaces.fsl import model as fslm
from nipype.pipeline import engine as pe

from ...interfaces.conditions import (
    ApplyConditionOffset,
    ParseConditionFile,
)
from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.make import MakeResultdicts
from ...interfaces.utility.tsv import FillNA
from ...utils.format import format_workflow
from ..memory import MemoryCalculator


def cond_bunch_to_lsa(subject_info):
    from nipype.interfaces.base import Bunch

    cb = subject_info[0] if isinstance(subject_info, list) else subject_info
    conditions, onsets, durations, amps = [], [], [], []
    for ci, cname in enumerate(cb.conditions):
        for ti, onset in enumerate(cb.onsets[ci]):
            tname = f"{cname}__{ti + 1:03d}"
            conditions.append(tname)
            onsets.append([onset])
            durations.append([cb.durations[ci][ti]])
            if getattr(cb, "amplitudes", None):
                amps.append([cb.amplitudes[ci][ti]])
            else:
                amps.append([1.0])

    return [
        Bunch(
            conditions=conditions,
            onsets=onsets,
            durations=durations,
            amplitudes=amps,
            tmod=None,
            pmod=None,
            regressor_names=None,
            regressors=None,
        )
    ]


def cond_bunch_to_lss(subject_info, mode="cond"):
    from nipype.interfaces.base import Bunch

    cb = subject_info[0] if isinstance(subject_info, list) else subject_info
    flat = []
    has_amp = getattr(cb, "amplitudes", None) is not None
    for ci, cname in enumerate(cb.conditions):
        for ti, onset in enumerate(cb.onsets[ci]):
            flat.append(
                dict(
                    cname=cname,
                    onset=onset,
                    duration=cb.durations[ci][ti],
                    amp=(cb.amplitudes[ci][ti] if has_amp else 1.0),
                    trial_id=ti + 1,
                )
            )
    cond_names = cb.conditions
    out = []
    for k, tr in enumerate(flat):
        roi = f"{tr['cname']}__{tr['trial_id']:03d}"
        conditions = [roi]
        onsets = [[tr["onset"]]]
        durations = [[tr["duration"]]]
        amplitudes = [[tr["amp"]]]
        others = [i for i in range(len(flat)) if i != k]
        if mode == "nuis":
            conditions.append("others")
            onsets.append([flat[i]["onset"] for i in others])
            durations.append([flat[i]["duration"] for i in others])
            amplitudes.append([flat[i]["amp"] for i in others])
        elif mode == "cond":
            for cname in cond_names:
                mask = [i for i in others if flat[i]["cname"] == cname]
                if mask:
                    conditions.append(f"{cname}_others")
                    onsets.append([flat[i]["onset"] for i in mask])
                    durations.append([flat[i]["duration"] for i in mask])
                    amplitudes.append([flat[i]["amp"] for i in mask])
        else:
            raise ValueError(mode)
        out.append(
            Bunch(
                conditions=conditions,
                onsets=onsets,
                durations=durations,
                amplitudes=amplitudes,
                tmod=None,
                pmod=None,
                regressor_names=None,
                regressors=None,
            )
        )
    return out


def plot_fsl_design(design_file, png_name=None):
    import os
    import pathlib

    import matplotlib.pyplot as plt
    import numpy as np

    rows, start = [], False
    for line in open(design_file):
        if line.strip() == "/Matrix":
            start = True
            continue
        if start:
            rows.append([float(x) for x in line.split()])
    X = np.array(rows)
    if png_name is None:
        stem = pathlib.Path(design_file).with_suffix("").name
        png_name = f"{stem}.png"
    out_png = os.path.abspath(png_name)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(X, aspect="auto", interpolation="nearest")
    ax.set_xlabel("Regressors")
    ax.set_ylabel("Time points")
    ax.set_title("FSL Design Matrix")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    return out_png


def pick_roi_betas(param_lists, idx=0):
    # param_lists: list of lists
    return [plist[idx] for plist in param_lists]


def _get_scan_start(vals) -> float:
    return float(vals["scan_start"])


def extract_conditions(subject_info):
    return {"trial_list": subject_info[0].conditions}


def init_singletrials_wf(
    workdir: Path | str,
    feature,
    condition_files,
    condition_units,
    memcalc=None,
):
    """
    Create a workflow that runs GLMsingle then dynamically builds and sinks
    resultdicts for each model in the nifti_outputs.
    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    if feature is not None:
        name = f"{format_workflow(feature.name)}_wf"
    else:
        name = "singletrials_wf"
    workflow = pe.Workflow(name=name)

    # Input & Output nodes
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "tags",
                "vals",
                "metadata",
                "bold",
                "mask",
                "repetition_time",
                "confounds_selected",
                "condition_names",
                "condition_files",
                "condition_units",
            ]
        ),
        name="inputnode",
    )
    inputnode.inputs.condition_names = feature.conditions
    inputnode.inputs.condition_files = condition_files
    inputnode.inputs.condition_units = condition_units

    outputnode = pe.Node(niu.IdentityInterface(fields=["resultdicts"]), name="outputnode")

    # ------------------------------------------------------------------
    # general
    parse_condition_file = pe.Node(ParseConditionFile(), name="parse_condition_file")

    get_scan_start = pe.Node(
        niu.Function(input_names=["vals"], output_names=["scan_start"], function=_get_scan_start), name="get_scan_start"
    )

    apply_condition_offset = pe.Node(ApplyConditionOffset(), name="apply_condition_offset")

    # generate design from first level specification
    if feature.hrf == "dgamma":
        bases: dict[str, dict] = dict(dgamma=dict())
    elif feature.hrf == "dgamma_with_derivs":
        bases = dict(dgamma=dict(derivs=True))
    elif feature.hrf == "flobs":
        bfcustompath = Path(os.environ["FSLDIR"]) / "etc" / "default_flobs.flobs" / "hrfbasisfns.txt"
        assert bfcustompath.is_file()
        bases = dict(
            custom=dict(
                bfcustompath=str(bfcustompath),
                basisfnum=3,
            )
        )
    else:
        raise ValueError(f'HRF "{feature.hrf}" is not yet implemented')

    #
    fillna = pe.Node(FillNA(), name="fillna")

    extract_conditions_node = pe.Node(
        niu.Function(
            input_names=["subject_info"],
            output_names=["trial_list"],
            function=extract_conditions,
        ),
        name="extract_conditions",
    )

    def merge_metadata(**kwargs):
        existing = kwargs.get("existing_metadata") or {}
        new = kwargs.get("new_metadata") or {}

        if not isinstance(existing, dict):
            raise TypeError(f"'existing_metadata' must be dict, got {type(existing)}")
        if not isinstance(new, dict):
            raise TypeError(f"'new_metadata' must be dict, got {type(new)}")

        merged = existing.copy()
        merged.update(new)
        return merged

    merge_metadata_node = pe.Node(
        niu.Function(input_names=["existing_metadata", "new_metadata"], output_names=["metadata"], function=merge_metadata),
        name="merge_metadata",
    )

    # ------------------------------------------------------------------
    # LSA
    cond2lsa = pe.Node(
        niu.Function(input_names=["subject_info"], output_names=["lsa_subject_info"], function=cond_bunch_to_lsa),
        name="cond2lsa",
    )

    spec_lsa = pe.Node(model.SpecifyModel(), name="specify_lsa")

    spec_lsa.inputs.high_pass_filter_cutoff = np.inf  # disable if missing
    if hasattr(feature, "high_pass_filter_cutoff"):
        hpfc = feature.high_pass_filter_cutoff
        if isinstance(hpfc, float) and isfinite(hpfc):
            spec_lsa.inputs.high_pass_filter_cutoff = hpfc

    l1_lsa = pe.Node(
        fslm.Level1Design(
            model_serial_correlations=True,
            bases=bases,
        ),
        name="l1design_lsa",
    )

    feat_lsa = pe.Node(FEATModel(), name="featmodel_lsa", mem_gb=1.0)

    film_lsa = pe.Node(FILMGLS(smooth_autocorr=True, mask_size=5), name="filmgls_lsa", mem_gb=memcalc.series_std_gb * 1.5)

    merge_lsa = pe.Node(
        Merge(dimension="t", output_type="NIFTI_GZ", merged_file="merged_betas.nii.gz"), name="merge_betas_lsa"
    )

    plot_lsa = pe.Node(
        niu.Function(input_names=["design_file", "png_name"], output_names=["out_png"], function=plot_fsl_design),
        name="plot_dm_lsa",
    )
    plot_lsa.inputs.png_name = "design_matrix_lsa.png"

    # ------------------------------------------------------------------
    # LSS
    cond2lss = pe.Node(
        niu.Function(input_names=["subject_info", "mode"], output_names=["lss_subject_infos"], function=cond_bunch_to_lss),
        name="cond2lss",
    )

    spec_lss = pe.MapNode(model.SpecifyModel(), iterfield=["subject_info"], name="specify_lss")

    spec_lss.inputs.high_pass_filter_cutoff = np.inf  # disable if missing
    if hasattr(feature, "high_pass_filter_cutoff"):
        hpfc = feature.high_pass_filter_cutoff
        if isinstance(hpfc, float) and isfinite(hpfc):
            spec_lss.inputs.high_pass_filter_cutoff = hpfc

    l1_lss = pe.MapNode(
        fslm.Level1Design(
            model_serial_correlations=True,
            bases=bases,
        ),
        iterfield=["session_info"],
        name="l1design_lss",
    )

    feat_lss = pe.MapNode(FEATModel(), iterfield=["fsf_file", "ev_files"], name="featmodel_lss", mem_gb=1.0)

    film_lss = pe.MapNode(
        FILMGLS(smooth_autocorr=True, mask_size=5),
        iterfield=["design_file"],
        name="filmgls_lss",
        mem_gb=memcalc.series_std_gb * 1.5,
    )

    pick_lss = pe.Node(
        niu.Function(input_names=["param_lists", "idx"], output_names=["roi_betas"], function=pick_roi_betas),
        name="pick_lss_betas",
    )

    pick_lss.inputs.idx = 0

    merge_lss = pe.Node(
        Merge(dimension="t", output_type="NIFTI_GZ", merged_file="merged_betas.nii.gz"), name="merge_betas_lss"
    )

    plot_lss = pe.MapNode(
        niu.Function(input_names=["design_file", "png_name"], output_names=["out_png"], function=plot_fsl_design),
        iterfield=["design_file"],
        name="plot_dm_lss",
    )

    # MapNode of MakeResultdicts over each input_dict
    merge_resultdicts = pe.Node(niu.Merge(2), name="merge_resultdicts")

    # could maybe be MapNode too..?
    make_resultdicts_lsa = pe.Node(
        MakeResultdicts(
            tagkeys=["feature", "model"],
            imagekeys=["effect"],
            metadatakeys=["sources"],
        ),
        name="make_resultdicts_lsa",
    )
    make_resultdicts_lsa.inputs.model = "lsa"

    make_resultdicts_lss = pe.Node(
        MakeResultdicts(
            tagkeys=["feature", "model"],
            imagekeys=["effect"],
            metadatakeys=["sources"],
        ),
        name="make_resultdicts_lss",
    )
    make_resultdicts_lss.inputs.model = "lss"

    # maybe just once in merge_resultdicts?
    if feature is not None:
        cond2lss.inputs.mode = feature.mode
        make_resultdicts_lss.inputs.feature = feature.name
        make_resultdicts_lsa.inputs.feature = feature.name

    # Datasink for final resultdicts
    resultdict_datasink = pe.Node(
        ResultdictDatasink(
            base_directory=str(workdir),
        ),
        name="resultdict_datasink",
    )

    # Connect the core graph
    workflow.connect(
        [
            # scan start offset
            (inputnode, get_scan_start, [("vals", "vals")]),
            (inputnode, fillna, [("confounds_selected", "in_tsv")]),
            (inputnode, merge_metadata_node, [("metadata", "existing_metadata")]),
            # parse conditions
            (inputnode, parse_condition_file, [("condition_names", "condition_names"), ("condition_files", "in_any")]),
            (get_scan_start, apply_condition_offset, [("scan_start", "scan_start")]),
            (parse_condition_file, apply_condition_offset, [("subject_info", "subject_info")]),
            # LSA
            (
                inputnode,
                spec_lsa,
                [("bold", "functional_runs"), ("repetition_time", "time_repetition"), ("condition_units", "input_units")],
            ),
            (apply_condition_offset, cond2lsa, [("subject_info", "subject_info")]),
            (cond2lsa, extract_conditions_node, [("lsa_subject_info", "subject_info")]),
            (cond2lsa, spec_lsa, [("lsa_subject_info", "subject_info")]),
            (fillna, spec_lsa, [("out_no_header", "realignment_parameters")]),
            (spec_lsa, l1_lsa, [("session_info", "session_info")]),
            (inputnode, l1_lsa, [("repetition_time", "interscan_interval")]),
            (l1_lsa, feat_lsa, [("fsf_files", "fsf_file"), ("ev_files", "ev_files")]),
            (feat_lsa, film_lsa, [("design_file", "design_file")]),
            (inputnode, film_lsa, [("bold", "in_file")]),
            (film_lsa, merge_lsa, [("param_estimates", "in_files")]),
            (feat_lsa, plot_lsa, [("design_file", "design_file")]),
            (
                inputnode,
                make_resultdicts_lsa,
                [
                    ("tags", "tags"),
                    ("vals", "vals"),
                    ("mask", "mask"),
                ],
            ),
            # add trial_list to metadata
            (extract_conditions_node, merge_metadata_node, [("trial_list", "new_metadata")]),
            (merge_metadata_node, make_resultdicts_lsa, [("metadata", "metadata")]),
            # LSS
            (
                inputnode,
                spec_lss,
                [("bold", "functional_runs"), ("repetition_time", "time_repetition"), ("condition_units", "input_units")],
            ),
            (apply_condition_offset, cond2lss, [("subject_info", "subject_info")]),
            (cond2lss, spec_lss, [("lss_subject_infos", "subject_info")]),
            (fillna, spec_lss, [("out_no_header", "realignment_parameters")]),
            (spec_lss, l1_lss, [("session_info", "session_info")]),
            (inputnode, l1_lss, [("repetition_time", "interscan_interval")]),
            (l1_lss, feat_lss, [("fsf_files", "fsf_file"), ("ev_files", "ev_files")]),
            (feat_lss, film_lss, [("design_file", "design_file")]),
            (inputnode, film_lss, [("bold", "in_file")]),
            (film_lss, pick_lss, [("param_estimates", "param_lists")]),
            (pick_lss, merge_lss, [("roi_betas", "in_files")]),
            (feat_lss, plot_lss, [("design_file", "design_file")]),
            (
                inputnode,
                make_resultdicts_lss,
                [
                    ("tags", "tags"),
                    ("vals", "vals"),
                    ("mask", "mask"),
                ],
            ),
            (merge_metadata_node, make_resultdicts_lss, [("metadata", "metadata")]),
            # populate beta files
            (merge_lsa, make_resultdicts_lsa, [("merged_file", "effect")]),
            (merge_lss, make_resultdicts_lss, [("merged_file", "effect")]),
            # merge dicts
            (make_resultdicts_lsa, merge_resultdicts, [("resultdicts", "in1")]),
            (make_resultdicts_lss, merge_resultdicts, [("resultdicts", "in2")]),
            # sink
            (merge_resultdicts, resultdict_datasink, [("out", "indicts")]),
            (merge_resultdicts, outputnode, [("out", "resultdicts")]),
        ]
    )

    return workflow
