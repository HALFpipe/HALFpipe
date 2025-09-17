# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from math import isfinite
from pathlib import Path
from typing import Literal

import nipype.algorithms.modelgen as model
import numpy as np
from nipype.interfaces import fsl
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from ...fixes.nodes import MapNode
from ...interfaces.conditions import ApplyConditionOffset, ParseConditionFile
from ...interfaces.fixes.level1design import Level1Design
from ...interfaces.image_maths.merge import Merge
from ...interfaces.result.datasink import ResultdictDatasink
from ...interfaces.result.make import MakeResultdicts
from ...interfaces.stats.dof import MakeDofVolume
from ...interfaces.utility.tsv import FillNA, MergeColumns
from ...interfaces.utility.vest import Unvest
from ...model.feature import Feature
from ...utils.format import format_workflow
from ...utils.ops import first_float, first_str
from ..memory import MemoryCalculator


def _add_temporal_derivative_conditions(hrf, condition_names):
    if hrf == "dgamma":
        return condition_names

    elif hrf == "dgamma_with_derivs":
        suffixes = ["", "TD"]

    elif hrf == "flobs":
        suffixes = ["", "FN2", "FN3"]  #

    else:
        raise ValueError(f'Unknown HRF "{hrf}"')

    return [f"{c}{suffix}" for c in condition_names for suffix in suffixes]


def _get_scan_start(vals) -> float:
    scan_start = vals["scan_start"]
    assert isinstance(scan_start, float)
    return scan_start


def _events(subject_info):
    return [subject_info]


def _least_squares_all_events(subject_info):
    from nipype.interfaces.base import Bunch

    if not isinstance(subject_info, Bunch):
        raise TypeError("subject_info must be a Bunch object")

    conditions: list[str] = list()
    onsets_lists: list[list[float]] = list()
    durations_lists: list[list[float]] = list()
    for condition, onsets, durations in zip(subject_info.conditions, subject_info.onsets, subject_info.durations, strict=True):
        digits = len(str(len(onsets)))

        for trial_index, (onset, duration) in enumerate(zip(onsets, durations, strict=True)):
            conditions.append(f"{condition}_{trial_index:0{digits}d}")
            onsets_lists.append([onset])
            durations_lists.append([duration])

    return [Bunch(conditions=conditions, onsets=onsets_lists, durations=durations_lists)]


def _least_squares_single_events(subject_info):
    from nipype.interfaces.base import Bunch

    if not isinstance(subject_info, Bunch):
        raise TypeError("subject_info must be a Bunch object")

    conditions: list[str] = subject_info.conditions
    onsets_lists: list[list[float]] = subject_info.onsets
    durations_lists: list[list[float]] = subject_info.durations

    subject_infos: list[Bunch] = list()

    for condition_index, (condition, onsets, durations) in enumerate(
        zip(conditions, onsets_lists, durations_lists, strict=True)
    ):
        # Prepare other conditions
        other_conditions = conditions.copy()
        other_conditions.pop(condition_index)
        other_onsets_lists = onsets_lists.copy()
        other_onsets_lists.pop(condition_index)
        other_duration_lists = durations_lists.copy()
        other_duration_lists.pop(condition_index)

        digits = len(str(len(onsets)))

        for trial_index, (onset, duration) in enumerate(zip(onsets, durations, strict=True)):
            other_onsets = onsets.copy()
            other_onsets.pop(trial_index)
            other_durations = durations.copy()
            other_durations.pop(trial_index)

            subject_infos.append(
                Bunch(
                    conditions=[f"{condition}_{trial_index:0{digits}d}", f"{condition}_others", *other_conditions],
                    onsets=[[onset], other_onsets, *other_onsets_lists],
                    durations=[[duration], other_durations, *other_duration_lists],
                )
            )

    return subject_infos


def _group_least_squares_all_parameter_estimates(subject_infos, param_estimates):
    from collections import defaultdict

    from nipype.interfaces.base import Bunch

    (subject_info,) = subject_infos
    (param_estimates,) = param_estimates
    if not isinstance(subject_info, Bunch):
        raise TypeError("subject_info must be a Bunch object")

    groups: dict[str, list[str]] = defaultdict(list)

    conditions = subject_info.conditions
    for condition, param_estimate in zip(conditions, param_estimates, strict=False):
        condition, _ = condition.rsplit("_", 1)  # Get condition name without trial index
        groups[condition].append(param_estimate)

    return list(groups.keys()), list(groups.values())


def _group_least_squares_single_parameter_estimates(subject_infos, param_estimates):
    from collections import defaultdict

    from nipype.interfaces.base import Bunch

    groups: dict[str, list[str]] = defaultdict(list)
    for subject_info, param_estimate in zip(subject_infos, param_estimates, strict=True):
        if not isinstance(subject_info, Bunch):
            raise TypeError("subject_info must be a Bunch object")

        conditions = subject_info.conditions
        condition, _ = conditions[0].rsplit("_", 1)  # Get condition name without trial index
        groups[condition].append(param_estimate[0])

    return list(groups.keys()), list(groups.values())


def init_task_based_wf(
    workdir: Path | str,
    feature: Feature,
    condition_files: tuple[str | tuple[str, str], ...],
    condition_units: Literal["secs", "scans"],
    space: Literal["standard", "native"] = "standard",
    memcalc: MemoryCalculator | None = None,
):
    """
    create workflow to calculate a first level glm for task functional data
    """
    memcalc = MemoryCalculator.default() if memcalc is None else memcalc
    if feature is not None:
        name = f"{format_workflow(feature.name)}_wf"
    else:
        name = "taskbased_wf"
    workflow = pe.Workflow(name=name)

    # Create input and output nodes
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

    # Parse condition files into three (ordered) lists
    parse_condition_file = pe.Node(ParseConditionFile(), name="parse_condition_file")
    workflow.connect(inputnode, "condition_names", parse_condition_file, "condition_names")
    workflow.connect(inputnode, "condition_files", parse_condition_file, "in_any")

    # Ensure correct event timings after removing dummy scans
    get_scan_start = pe.Node(
        niu.Function(input_names=["vals"], output_names=["scan_start"], function=_get_scan_start),
        name="get_scan_start",
    )
    workflow.connect(inputnode, "vals", get_scan_start, "vals")

    apply_condition_offset = pe.Node(ApplyConditionOffset(), name="apply_condition_offset")
    workflow.connect(parse_condition_file, "subject_info", apply_condition_offset, "subject_info")
    workflow.connect(get_scan_start, "scan_start", apply_condition_offset, "scan_start")

    # Generate design from first level specification
    if feature.hrf == "dgamma":
        bases: dict[str, dict] = dict(dgamma=dict())
    elif feature.hrf == "dgamma_with_derivs":
        bases = dict(dgamma=dict(derivs=True))
    elif feature.hrf == "flobs":
        flobs_path = Path(os.environ["FSLDIR"]) / "etc" / "default_flobs.flobs" / "hrfbasisfns.txt"
        if not flobs_path.is_file():
            raise FileNotFoundError(f"FLOBS basis function file {flobs_path} does not exist. ")
        bases = dict(
            custom=dict(
                bfcustompath=str(flobs_path),
                basisfnum=3,
            )
        )
    else:
        raise ValueError(f'HRF "{feature.hrf}" is not available')

    # Replace NaN values in confounds with 0.0
    fill_na = pe.Node(FillNA(), name="fill_na")
    workflow.connect(inputnode, "confounds_selected", fill_na, "in_tsv")

    # Transform contrasts dictionary to Nipype list data structure
    contrasts: list[tuple[str, str, list[str], list[float]]] = list()
    if feature.contrasts is not None:
        condition_names = feature.conditions
        for contrast in feature.contrasts:
            contrast_values = [contrast["values"].get(c, 0.0) for c in condition_names]
            contrasts.append(
                (
                    contrast["name"],
                    contrast["type"].upper(),
                    condition_names,
                    contrast_values,
                )
            )
        parse_condition_file.inputs.contrasts = contrasts

    # Optionally transform events for single trial estimation

    _create_subject_infos = dict(
        multiple_trial=_events,
        single_trial_least_squares_single=_least_squares_single_events,
        single_trial_least_squares_all=_least_squares_all_events,
    )[feature.estimation]
    create_subject_infos = pe.Node(
        niu.Function(
            input_names=["subject_info"],
            output_names=["subject_info"],
            function=_create_subject_infos,
        ),
        name="create_subject_infos",
    )
    workflow.connect(apply_condition_offset, "subject_info", create_subject_infos, "subject_info")

    # First level model specification
    specify_model = pe.MapNode(model.SpecifyModel(), iterfield=["subject_info"], name="specify_model")

    specify_model.inputs.high_pass_filter_cutoff = np.inf  # disable if missing
    if hasattr(feature, "high_pass_filter_cutoff"):
        hpfc = feature.high_pass_filter_cutoff
        if isinstance(hpfc, float) and isfinite(hpfc):
            specify_model.inputs.high_pass_filter_cutoff = hpfc

    workflow.connect(inputnode, "bold", specify_model, "functional_runs")
    workflow.connect(inputnode, "condition_units", specify_model, "input_units")
    workflow.connect(inputnode, "repetition_time", specify_model, "time_repetition")
    workflow.connect(fill_na, "out_no_header", specify_model, "realignment_parameters")

    workflow.connect(create_subject_infos, "subject_info", specify_model, "subject_info")

    level1_design = pe.MapNode(
        Level1Design(
            model_serial_correlations=feature.model_serial_correlations,
            bases=bases,
        ),
        iterfield=["session_info"],
        name="level1_design",
    )
    workflow.connect(parse_condition_file, "contrasts", level1_design, "contrasts")
    workflow.connect(inputnode, "repetition_time", level1_design, "interscan_interval")
    workflow.connect(specify_model, "session_info", level1_design, "session_info")

    # Generate required input files for FILMGLS from design
    feat_model = pe.MapNode(fsl.FEATModel(), iterfield=["fsf_file", "ev_files"], name="feat_model", mem_gb=1.0)
    workflow.connect(level1_design, "fsf_files", feat_model, "fsf_file")
    workflow.connect(level1_design, "ev_files", feat_model, "ev_files")
    # TODO: Also output design_image

    # Calculate range of image values to determine cutoff value
    # FILMGLS will use this to shrink the brain mask
    calculate_range = pe.Node(
        fsl.ImageStats(op_string="-R"),
        name="calculate_range",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "bold", calculate_range, "in_file")
    cutoff = pe.Node(
        niu.Function(input_names=["obj"], output_names="min_val", function=first_float),
        name="cutoff",
    )
    workflow.connect(calculate_range, "out_stat", cutoff, "obj")

    # Estimate the first level model
    model_estimate = MapNode(
        fsl.FILMGLS(
            smooth_autocorr=feature.model_serial_correlations,
            mask_size=5,
        ),
        iterfield=["design_file", "tcon_file"],
        allow_undefined_iterfield=True,
        name="model_estimate",
        mem_gb=memcalc.series_std_gb * 1.5,
    )
    workflow.connect(inputnode, "bold", model_estimate, "in_file")
    workflow.connect(cutoff, "min_val", model_estimate, "threshold")
    workflow.connect(feat_model, "design_file", model_estimate, "design_file")
    workflow.connect(feat_model, "con_file", model_estimate, "tcon_file")

    # Transform outputs
    merge_resultdicts = pe.Node(niu.Merge(2), name="merge_resultdicts")

    if feature.estimation == "multiple_trial":
        # Make degrees of freedom volume
        make_degrees_of_freedom_volume = pe.Node(
            MakeDofVolume(),
            iterfield=["dof_file", "copes"],
            name="make_degrees_of_freedom_volume",
        )
        workflow.connect([(model_estimate, make_degrees_of_freedom_volume, [(("copes", first_str), "copes")])])
        workflow.connect([(model_estimate, make_degrees_of_freedom_volume, [(("dof_file", first_str), "dof_file")])])

        # Output design and contrast matrices
        merge_column_names = pe.Node(niu.Merge(2), name="merge_column_names")
        workflow.connect(fill_na, "column_names", merge_column_names, "in2")

        if feature.hrf != "dgamma":
            add_temporal_derivative_conditions = pe.Node(
                niu.Function(
                    input_names=["hrf", "condition_names"],
                    output_names="condition_names",
                    function=_add_temporal_derivative_conditions,
                ),
                name="add_temporal_derivative_conditions",
            )
            add_temporal_derivative_conditions.inputs.hrf = feature.hrf
            workflow.connect(
                parse_condition_file,
                "condition_names",
                add_temporal_derivative_conditions,
                "condition_names",
            )

            workflow.connect(add_temporal_derivative_conditions, "condition_names", merge_column_names, "in1")
        else:
            workflow.connect(parse_condition_file, "condition_names", merge_column_names, "in1")

        design_unvest = pe.Node(Unvest(), name="design_unvest")
        workflow.connect([(feat_model, design_unvest, [(("design_file", first_str), "in_vest")])])

        design_tsv = pe.Node(MergeColumns(1), name="design_tsv")
        workflow.connect(design_unvest, "out_no_header", design_tsv, "in1")
        workflow.connect(merge_column_names, "out", design_tsv, "column_names1")

        contrast_unvest = pe.Node(Unvest(), name="contrast_unvest")
        workflow.connect([(feat_model, contrast_unvest, [(("con_file", first_str), "in_vest")])])

        contrast_tsv = pe.Node(MergeColumns(1), name="contrast_tsv")
        workflow.connect(parse_condition_file, "contrast_names", contrast_tsv, "row_index")
        workflow.connect(contrast_unvest, "out_no_header", contrast_tsv, "in1")
        workflow.connect(merge_column_names, "out", contrast_tsv, "column_names1")

        make_design_resultdicts = pe.Node(
            MakeResultdicts(tagkeys=["feature"], imagekeys=["design_matrix", "contrast_matrix"]),
            name="make_design_resultdicts",
        )
        make_design_resultdicts.inputs.feature = feature.name
        workflow.connect(inputnode, "tags", make_design_resultdicts, "tags")
        workflow.connect(inputnode, "vals", make_design_resultdicts, "vals")
        workflow.connect(inputnode, "metadata", make_design_resultdicts, "metadata")

        workflow.connect(design_tsv, "out_with_header", make_design_resultdicts, "design_matrix")
        workflow.connect(contrast_tsv, "out_with_header", make_design_resultdicts, "contrast_matrix")

        workflow.connect(make_design_resultdicts, "resultdicts", merge_resultdicts, "in1")

        # Make resultdicts from model estimates
        make_resultdicts = pe.Node(
            MakeResultdicts(
                tagkeys=["feature", "taskcontrast"],
                imagekeys=["effect", "variance", "sigmasquareds", "z", "dof", "mask"],
            ),
            name="make_resultdicts",
        )

        make_resultdicts.inputs.feature = feature.name
        workflow.connect(inputnode, "tags", make_resultdicts, "tags")
        workflow.connect(inputnode, "vals", make_resultdicts, "vals")
        workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")
        workflow.connect(inputnode, "mask", make_resultdicts, "mask")

        workflow.connect(model_estimate, "copes", make_resultdicts, "effect")
        workflow.connect(model_estimate, "varcopes", make_resultdicts, "variance")
        workflow.connect(model_estimate, "sigmasquareds", make_resultdicts, "sigmasquareds")
        workflow.connect(model_estimate, "zstats", make_resultdicts, "z")
        workflow.connect(make_degrees_of_freedom_volume, "out_file", make_resultdicts, "dof")

        workflow.connect(parse_condition_file, "contrast_names", make_resultdicts, "taskcontrast")

        workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")
        workflow.connect(make_resultdicts, "resultdicts", merge_resultdicts, "in2")
    elif feature.estimation in {
        "single_trial_least_squares_single",
        "single_trial_least_squares_all",
    }:
        _group_parameter_estimates = dict(
            single_trial_least_squares_single=_group_least_squares_single_parameter_estimates,
            single_trial_least_squares_all=_group_least_squares_all_parameter_estimates,
        )[feature.estimation]

        # Group parameter estimates by condition
        group_parameter_estimates = pe.Node(
            niu.Function(
                input_names=["subject_infos", "param_estimates"],
                output_names=["conditions", "param_estimates"],
                function=_group_parameter_estimates,
            ),
            name="group_parameter_estimates",
        )
        workflow.connect(create_subject_infos, "subject_info", group_parameter_estimates, "subject_infos")
        workflow.connect(model_estimate, "param_estimates", group_parameter_estimates, "param_estimates")

        # Make resultdicts from model estimates
        merge_parameter_estimates = pe.MapNode(
            Merge(dimension="t"),
            iterfield="in_files",
            name="merge_parameter_estimates",
            mem_gb=memcalc.volume_std_gb * 3,
        )
        workflow.connect(group_parameter_estimates, "param_estimates", merge_parameter_estimates, "in_files")

        make_resultdicts = pe.Node(
            MakeResultdicts(
                tagkeys=["feature", "condition"],
                imagekeys=["effect", "mask"],
            ),
            name="make_resultdicts",
        )
        make_resultdicts.inputs.feature = feature.name
        workflow.connect(inputnode, "tags", make_resultdicts, "tags")
        workflow.connect(inputnode, "vals", make_resultdicts, "vals")
        workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")
        workflow.connect(inputnode, "mask", make_resultdicts, "mask")

        workflow.connect(group_parameter_estimates, "conditions", make_resultdicts, "condition")
        workflow.connect(merge_parameter_estimates, "merged_file", make_resultdicts, "effect")

        workflow.connect(make_resultdicts, "resultdicts", merge_resultdicts, "in2")
    else:
        raise ValueError(f'Unknown estimation "{feature.estimation}"')

    resultdict_datasink = pe.Node(ResultdictDatasink(base_directory=workdir), name="resultdict_datasink")
    workflow.connect(merge_resultdicts, "out", resultdict_datasink, "indicts")

    return workflow
