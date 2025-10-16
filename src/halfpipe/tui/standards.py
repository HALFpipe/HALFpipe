from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Union

from inflection import humanize

global_settings_defaults: dict[str, str] = {
    "dummy_scans": "0",
    "run_reconall": "False",
    "slice_timing": "False",
    "skull_strip_algorithm": "ants",
}
opts: dict[str, str | bool | Path | None] = {
    "debug": False,
    "verbose": False,
    "watchdog": False,
    "keep": "some",
    "workdir": None,
}


bandpass_filter_defaults: dict[str, dict] = {
    "gaussian": {"type": "gaussian", "hp_width": "125", "lp_width": None},
    "frequency_based": {"type": "frequency_based", "high": "0.1", "low": "0.01"},
}

# specify first task based defaults, for other features we will just copy it and modify what is different
task_based_defaults: Dict[
    str,
    Union[
        Dict[str, Union[str, int, float, None, List[Union[str, bool]]]],
        List[Dict[str, Union[str, float]]],
        str,
        float,
    ],
] = {
    "bandpass_filter": {"type": "gaussian", "hp_width": "125", "lp_width": None},
    "smoothing": {"fwhm": "6"},
    "grand_mean_scaling": {"mean": 10000},
    "confounds_options": {
        "ICA-AROMA": ["ICA-AROMA", False],
        "(trans|rot)_[xyz]": ["Motion parameters", False],
        "(trans|rot)_[xyz]_derivative1": ["Derivatives of motion parameters", False],
        "(trans|rot)_[xyz]_power2": ["Motion parameters squared", False],
        "(trans|rot)_[xyz]_derivative1_power2": ["Derivatives of motion parameters squared", False],
        "motion_outlier[0-9]+": ["Motion scrubbing", False],
        "a_comp_cor_0[0-4]": ["aCompCor (top five components)", False],
        "white_matter": ["White matter signal", False],
        "csf": ["CSF signal", False],
        "global_signal": ["Global signal", False],
    },
}

seed_based_defaults = deepcopy(task_based_defaults)
seed_based_defaults["minimum_coverage_label"] = "Minimum fMRI brain coverage by seed (in fraction)"
seed_based_defaults["widget_header"] = "Seed images"
seed_based_defaults["file_selection_widget_header"] = "Select seeds"
seed_based_defaults["minimum_brain_coverage"] = 0.8

dual_reg_defaults = deepcopy(task_based_defaults)
dual_reg_defaults["minimum_coverage_label"] = "Minimum network template coverage by individual brain mask (in fraction)"
dual_reg_defaults["widget_header"] = "Network template images"
dual_reg_defaults["file_selection_widget_header"] = "Select network templates"
dual_reg_defaults["minimum_brain_coverage"] = 0.8

gig_ica_defaults = deepcopy(dual_reg_defaults)

preproc_output_defaults = deepcopy(task_based_defaults)
preproc_output_defaults["minimum_coverage_label"] = "None"
preproc_output_defaults["widget_header"] = "None"
preproc_output_defaults["file_selection_widget_header"] = "None"

atlas_based_connectivity_defaults = deepcopy(task_based_defaults)
atlas_based_connectivity_defaults["bandpass_filter"] = {"type": "frequency_based", "high": "0.1", "low": "0.01"}
atlas_based_connectivity_defaults["smoothing"] = {"fwhm": None}
atlas_based_connectivity_defaults["minimum_brain_coverage"] = 0.8
atlas_based_connectivity_defaults["minimum_coverage_label"] = (
    "Minimum atlas region coverage by individual brain mask (in fraction)"
)
atlas_based_connectivity_defaults["widget_header"] = "Atlas images"
atlas_based_connectivity_defaults["file_selection_widget_header"] = "Select atlases"

# reho and falff have same configuration
reho_defaults = deepcopy(atlas_based_connectivity_defaults)
# pop unused keys
reho_defaults.pop("minimum_coverage_label")
reho_defaults.pop("widget_header")
reho_defaults.pop("file_selection_widget_header")
# bring back smoothing because it was None at Atlas
reho_defaults["smoothing"] = {"fwhm": "6"}
falff_defaults = deepcopy(reho_defaults)

group_level_modesl_defaults: dict[str, list[dict[str, str]]] = {
    "cutoffs": [
        {
            "type": "cutoff",
            "action": "exclude",
            "field": "fd_mean",
            "cutoff": "0.5",
        },
        {
            "type": "cutoff",
            "action": "exclude",
            "field": "fd_perc",
            "cutoff": "10.0",
        },
    ]
}

# this maps how feature labels are viewed in the UI by the use, change value to change the label
feature_label_map: dict[str, str] = {
    "task_based": "Task-based",
    "seed_based_connectivity": "Seed-based connectivity",
    "dual_regression": "Network Template Regression (dual regression)",
    "gig_ica": "Network Template Regression (Neuromark)",
    "atlas_based_connectivity": "Atlas-based Connectivity",
    "reho": "ReHo",
    "falff": "fALFF",
    "preprocessed_image": "Output preprocessed image",
}

# same as above, but for group level models
group_level_model_label_map: dict[str, str] = {"me": "Intercept-only", "lme": "Linear model"}

# colors of the entity highlight in the path pattern builder
entity_colors: dict[str, str] = {
    "sub": "red",
    "ses": "green",
    "run": "magenta",
    "task": "cyan",
    "dir": "yellow",
    "condition": "orange",
    "acq": "purple",  # Changed to purple for uniqueness
    "echo": "brown",  # Changed to brown for uniqueness
    "desc": "red",  # there is only one entity when desc is used
}

# same as above but for field maps
field_map_group_labels: dict[str, str] = {
    "epi": "EPI (blip-up blip-down)",
    "siemens": "Phase difference and magnitude (used by Siemens scanners)",
    "philips": "Scanner-computed field map and magnitude (used by GE / Philips scanners)",
}

field_map_labels: dict[str, str] = {
    "magnitude1": "first set of magnitude image",
    "magnitude2": "second set of magnitude image",
    "phase1": "first set of phase image",
    "phase2": "second set of phase image",
    "phasediff": "phase difference image",
    "fieldmap": "field map image",
}


# function for displaying some labels in the meta_data_steps
def display_str(x):
    """
    Formats a string for display, handling specific cases.

    Parameters
    ----------
    x : str
        The input string to format.

    Returns
    -------
    str
        The formatted string.
    """
    if x == "MNI152NLin6Asym":
        return "MNI ICBM 152 non-linear 6th Generation Asymmetric (FSL)"
    elif x == "MNI152NLin2009cAsym":
        return "MNI ICBM 2009c Nonlinear Asymmetric"
    elif x == "slice_encoding_direction":
        return "slice acquisition direction"
    return humanize(x)


aggregate_order = ["dir", "run", "ses", "task"]
