# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

from fmriprep import config
from fmriprep.cli.workflow import build_workflow
from nipype.interfaces.base.traits_extension import isdefined
from nipype.pipeline import engine as pe
from packaging.version import Version

from ..collect.fmap import collect_fieldmaps
from ..logging import logger
from ..utils.copy import deepcopyfactory
from ..utils.format import inflect_engine as p
from .constants import Constants
from .factory import Factory
from .memory import MemoryCalculator
from .reports import init_anat_report_wf, init_func_report_wf


def get_fmriprep_wf_name() -> str:
    ver = Version(config.environment.version)
    return f"fmriprep_{ver.major}_{ver.minor}_wf"


@dataclass(frozen=True, kw_only=True)
class Connection:
    source: Literal["anat_fit_wf", "bold_wf", "reports_wf"]
    path: tuple[str, ...]
    attr: str


connections = {
    "anat2std_xfm": Connection(
        source="anat_fit_wf",
        path=("register_template_wf", "outputnode"),
        attr="anat2std_xfm",
    ),
    "std2anat_xfm": Connection(
        source="anat_fit_wf",
        path=("register_template_wf", "outputnode"),
        attr="std2anat_xfm",
    ),
    "ds_t1w_dseg_mask_report": Connection(
        source="anat_fit_wf",
        path=("anat_reports_wf", "ds_t1w_dseg_mask_report"),
        attr="out_file",
    ),
    "mask_std": Connection(
        source="anat_fit_wf",
        path=("anat_reports_wf", "mask_std"),
        attr="output_image",
    ),
    "t1w_dseg": Connection(
        source="anat_fit_wf",
        path=("outputnode",),
        attr="t1w_dseg",
    ),
    "t1w_mask": Connection(
        source="anat_fit_wf",
        path=("outputnode",),
        attr="t1w_mask",
    ),
    "t1w_preproc": Connection(
        source="anat_fit_wf",
        path=("outputnode",),
        attr="t1w_preproc",
    ),
    "t1w_std": Connection(
        source="anat_fit_wf",
        path=("anat_reports_wf", "t1w_std"),
        attr="output_image",
    ),
    "template": Connection(
        source="anat_fit_wf",
        path=("register_template_wf", "outputnode"),
        attr="template",
    ),
    "bold_file_std": Connection(
        source="bold_wf",
        path=("bold_std_wf", "outputnode"),
        attr="bold_file",
    ),
    "bold_mask_std": Connection(
        source="bold_wf",
        path=("ds_bold_std_wf", "ds_mask"),
        attr="out_file",
    ),
    "bold_file_anat": Connection(
        source="bold_wf",
        path=("bold_anat_wf", "outputnode"),
        attr="bold_file",
    ),
    "bold_mask_anat": Connection(
        source="bold_wf",
        path=("ds_bold_t1_wf", "ds_mask"),
        attr="out_file",
    ),
    "bold_ref_anat": Connection(
        source="bold_wf",
        path=("ds_bold_t1_wf", "ds_ref"),
        attr="out_file",
    ),
    "bold_file_native": Connection(
        # BOLD series resampled into BOLD reference space. Slice-timing,
        # head motion and susceptibility distortion correction (STC, HMC, SDC)
        # will all be applied to each file. For multi-echo data, the echos
        # are combined to form an `optimal combination`_.
        source="bold_wf",
        path=("bold_native_wf", "outputnode"),
        attr="bold_native",
    ),
    "bold_mask_native": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "outputnode"),
        attr="bold_mask",
    ),
    "bold_minimal": Connection(
        # BOLD series ready for further resampling. For single-echo data, only
        # slice-timing correction (STC) may have been applied. For multi-echo
        # data, this is identical to bold_native.
        source="bold_wf",
        path=("bold_native_wf", "outputnode"),
        attr="bold_minimal",
    ),
    "boldref2anat_xfm": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "outputnode"),
        attr="boldref2anat_xfm",
    ),
    "confounds_file": Connection(
        source="bold_wf",
        path=("bold_confounds_wf", "outputnode"),
        attr="confounds_file",
    ),
    "coreg_boldref": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "outputnode"),
        attr="coreg_boldref",
    ),
    "ds_ref": Connection(
        source="bold_wf",
        path=("ds_bold_std_wf", "ds_ref"),
        attr="out_file",
    ),
    "ds_report_bold_conf": Connection(
        source="bold_wf",
        path=("carpetplot_wf", "ds_report_bold_conf"),
        attr="out_file",
    ),
    "ds_report_bold_rois": Connection(
        source="bold_wf",
        path=("bold_confounds_wf", "ds_report_bold_rois"),
        attr="out_file",
    ),
    "ds_report_compcor": Connection(
        source="bold_wf",
        path=("bold_confounds_wf", "ds_report_compcor"),
        attr="out_file",
    ),
    "ds_report_conf_corr": Connection(
        source="bold_wf",
        path=("bold_confounds_wf", "ds_report_conf_corr"),
        attr="out_file",
    ),
    "ds_report_summary": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "func_fit_reports_wf", "ds_report_summary"),
        attr="out_file",
    ),
    "ds_report_validation": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "func_fit_reports_wf", "ds_report_validation"),
        attr="out_file",
    ),
    "dummy_scans": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "outputnode"),
        attr="dummy_scans",
    ),
    "fallback": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "bold_reg_wf", "outputnode"),
        attr="fallback",
    ),
    "motion_xfm": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "outputnode"),
        attr="motion_xfm",
    ),
    "sdc_method": Connection(
        source="bold_wf",
        path=("bold_fit_wf", "fmap_select"),
        attr="sdc_method",
    ),
    "vals": Connection(
        source="reports_wf",
        path=("func_report_wf", "outputnode"),
        attr="vals",
    ),
}


class FmriprepFactory(Factory):
    def __init__(self, ctx):
        super(FmriprepFactory, self).__init__(ctx)

    def setup(self, workdir: Path, bold_file_paths: set[str]) -> set[str]:
        """
        This needs to be documented.
        """

        spec = self.ctx.spec
        database = self.ctx.database
        bids_database = self.ctx.bids_database
        workflow = self.ctx.workflow

        subjects = set()
        bids_subjects: set[str] = set()
        bids_subject_sessions: dict[str, set[str]] = defaultdict(set)
        for bold_file_path in bold_file_paths:
            subject = database.tagval(bold_file_path, "sub")

            if subject is None:
                continue

            bids_path = bids_database.to_bids(bold_file_path)
            assert bids_path is not None
            bids_subject = bids_database.get_tag_value(bids_path, "subject")

            if bids_subject is None:
                continue

            subjects.add(subject)
            bids_subjects.add(bids_subject)

            bids_session = bids_database.get_tag_value(bids_path, "session")
            if bids_session is not None:
                bids_subject_sessions[bids_subject].add(bids_session)

        processing_groups = [
            (bids_subject, list(bids_subject_sessions[bids_subject]) if bids_subject_sessions[bids_subject] else None)
            for bids_subject in bids_subjects
        ]

        spec = self.ctx.spec
        global_settings = spec.global_settings

        config_file = self.get_config(workdir, bids_subjects, processing_groups)

        retval: dict[str, pe.Workflow] = dict()
        # We call build_workflow to set up all nodes
        with patch("niworkflows.utils.misc.check_valid_fs_license") as mock:
            mock.return_value = True
            build_workflow(config_file, retval)

        fmriprep_wf = retval["workflow"]
        assert isinstance(fmriprep_wf, pe.Workflow)
        workflow.add_nodes([fmriprep_wf])

        # check and patch workflow
        skipped = set()
        for bold_file_path in bold_file_paths:
            func_preproc_wf = self._get_hierarchy(get_fmriprep_wf_name(), source_file=bold_file_path)[-1]

            if not isinstance(func_preproc_wf, pe.Workflow) or len(func_preproc_wf._graph) == 0:
                logger.warning(f'fMRIPrep skipped processing for file "{bold_file_path}"')
                skipped.add(bold_file_path)
                continue

            bold_fit_wf = func_preproc_wf.get_node("bold_fit_wf")
            if bold_fit_wf is None:
                raise RuntimeError(f'Missing bold_fit_wf in "{func_preproc_wf.name}"')

            has_fieldmaps = len(collect_fieldmaps(database, bold_file_path, silent=True)) > 0
            if has_fieldmaps:
                if bold_fit_wf.get_node("fmap_select") is None:
                    logger.warning(f'fMRIPrep did not detect field maps for file "{bold_file_path}"')

            if global_settings["slice_timing"]:
                bold_native_wf = func_preproc_wf.get_node("bold_native_wf")
                if bold_native_wf.get_node("bold_stc_wf") is None:
                    logger.warning(f'fMRIPrep did not find slice timing metadata for file "{bold_file_path}"')

            # Disable preproc output to save disk space
            for name in {"ds_bold_t1_wf", "ds_bold_std_wf"}:
                ds_volumes_wf = func_preproc_wf.get_node(name)
                # ! func_derivatives_wf does not exist anymore, but ds_bold_std is part of bold workflows
                if not isinstance(ds_volumes_wf, pe.Workflow):
                    raise ValueError(f'Missing "{name}" in "{func_preproc_wf.name}"')
                ds_bold = ds_volumes_wf.get_node("ds_bold")
                if not isinstance(ds_bold, pe.Node):
                    raise ValueError(f'Missing "ds_bold" in "{name}"')
                ds_volumes_wf.remove_nodes([ds_bold])

        bold_file_paths -= skipped

        # halfpipe-specific report workflows
        anat_report_wf_factory = deepcopyfactory(init_anat_report_wf(workdir=str(workdir)))
        for subject_id in subjects:
            hierarchy = self._get_hierarchy("reports_wf", subject_id=subject_id)

            wf = anat_report_wf_factory()
            hierarchy[-1].add_nodes([wf])
            hierarchy.append(wf)

            inputnode = wf.get_node("inputnode")
            inputnode.inputs.tags = {"sub": subject_id}

            self.connect(hierarchy, inputnode, subject_id=subject_id)

        for bold_file_path in bold_file_paths:
            hierarchy = self._get_hierarchy("reports_wf", source_file=bold_file_path)

            wf = init_func_report_wf(
                workdir=str(workdir),
                memcalc=MemoryCalculator.from_bold_file(bold_file_path),
            )
            assert wf.name == "func_report_wf"  # check name for line 206
            hierarchy[-1].add_nodes([wf])
            hierarchy.append(wf)

            inputnode = wf.get_node("inputnode")
            assert isinstance(inputnode, pe.Node)
            inputnode.inputs.tags = database.tags(bold_file_path)
            inputnode.inputs.fd_thres = global_settings["fd_thres"]

            inputnode.inputs.repetition_time = database.metadata(bold_file_path, "repetition_time")

            self.connect(hierarchy, inputnode, source_file=bold_file_path)

        return bold_file_paths

    def get_config(
        self, workdir: Path, bids_subjects: set[str], processing_groups: list[tuple[str, list[str] | None]]
    ) -> Path:
        spec = self.ctx.spec
        global_settings = spec.global_settings
        workflow = self.ctx.workflow

        # init fmriprep config
        output_dir = Path(workdir) / "derivatives"
        output_dir.mkdir(parents=True, exist_ok=True)

        fmriprep_dir = output_dir / "fmriprep"
        fmriprep_dir.mkdir(parents=True, exist_ok=True)

        uuidstr = str(workflow.uuid)[:8]
        bids_dir = Path(workdir) / "rawdata"

        ignore = []
        if global_settings["slice_timing"] is not True:
            ignore.append("slicetiming")

        skull_strip_t1w = {
            "none": "skip",
            "auto": "auto",
            "ants": "force",
        }[global_settings["skull_strip_algorithm"]]

        # reset fmriprep config
        config.execution.bids_database_dir = None
        config.execution._layout = None
        config.execution.layout = None

        output_spaces = ["anat", f"{Constants.reference_space}:res-{Constants.reference_res}"]

        if global_settings["run_reconall"]:
            output_spaces.append("fsaverage:den-164k")
            output_spaces.append("fsnative")

        # create config
        config.from_dict(
            {
                #
                "bids_dir": bids_dir,  # input directory
                "output_dir": output_dir,  # derivatives folder
                "fmriprep_dir": fmriprep_dir,  # fmriprep subfolder
                "log_dir": str(workdir),  # put crash files directly in working directory
                "work_dir": str(workdir / ".fmriprep"),  # where toml configuration files will go
                "output_layout": "legacy",  # do not yet use the new layout
                "participant_label": sorted(bids_subjects),  # include all subjects
                "write_graph": global_settings["write_graph"],
                # smriprep config
                "anat_only": global_settings["anat_only"],
                "skull_strip_t1w": skull_strip_t1w,
                "skull_strip_fixed_seed": global_settings["skull_strip_fixed_seed"],
                "skull_strip_template": global_settings["skull_strip_template"],
                # freesurfer config
                "run_reconall": global_settings["run_reconall"],
                "hires": global_settings["hires"],
                "cifti_output": False,  # we do this in halfpipe
                "t2s_coreg": global_settings["t2s_coreg"],
                "medial_surface_nan": global_settings["medial_surface_nan"],
                "longitudinal": global_settings["longitudinal"],
                #
                "dummy_scans": global_settings["dummy_scans"],  # remove initial non-steady state volumes
                # bold_reg_wf config
                "use_bbr": global_settings["use_bbr"],
                "bold2anat_dof": global_settings["bold2t1w_dof"],  # this one changed name in new fmriprep
                # sdcflows config
                "fmap_bspline": global_settings["fmap_bspline"],
                "force_syn": global_settings["force_syn"],
                #
                "force": list(),
                "ignore": ignore,  # used to disable slice timing
                # ica_aroma_wf settings
                "use_aroma": False,  # we do this in halfpipe
                "aroma_err_on_warn": global_settings["aroma_err_on_warn"],
                "aroma_melodic_dim": global_settings["aroma_melodic_dim"],
                #
                "regressors_all_comps": global_settings["regressors_all_comps"],
                "regressors_dvars_th": global_settings["regressors_dvars_th"],
                "regressors_fd_th": global_settings["regressors_fd_th"],
                #
                "output_spaces": " ".join(output_spaces),
                #
                "sloppy": global_settings["sloppy"],  # used for unit testing,
                #
                "level": "full",
            }
        )
        config.execution.processing_groups = processing_groups

        nipype_dir = Path(workdir) / Constants.workflow_directory
        nipype_dir.mkdir(parents=True, exist_ok=True)
        config_file = nipype_dir / f"fmriprep.config.{uuidstr}.toml"
        config.to_filename(config_file)
        return config_file

    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)  # type: ignore

    def connect(
        self,
        nodehierarchy: list[pe.Workflow],
        node: pe.Node,
        source_file: Path | str | None = None,
        subject_id: str | None = None,
        ignore_attrs: frozenset[str] = frozenset({"alt_bold_file_std", "alt_bold_mask_std"}),
        **_: Any,
    ) -> set[str]:
        """
        This method connects equally named attributes of nodes
        """

        fullname = ".".join([n.name for n in nodehierarchy] + [node.name])
        logger.debug(f"Connecting node '{fullname}'")

        hierarchies: dict[Literal["anat_fit_wf", "bold_wf", "reports_wf"], list[pe.Workflow]] = dict()

        bold_wf_hierarchy = self._get_hierarchy(get_fmriprep_wf_name(), source_file=source_file, subject_id=subject_id)
        hierarchies["bold_wf"] = bold_wf_hierarchy

        anat_fit_wf_hierarchy = bold_wf_hierarchy.copy()
        while (anat_fit_wf := anat_fit_wf_hierarchy[-1].get_node("anat_fit_wf")) is None:
            anat_fit_wf_hierarchy.pop(-1)
        anat_fit_wf_hierarchy.append(anat_fit_wf)
        hierarchies["anat_fit_wf"] = anat_fit_wf_hierarchy

        report_wf_hierarchy = self._get_hierarchy("reports_wf", source_file=source_file, subject_id=subject_id)
        hierarchies["reports_wf"] = report_wf_hierarchy

        connected_attrs: set[str] = set()
        missing_attrs: set[str] = set()
        for key, value in node.inputs.get().items():
            if isdefined(value):
                continue

            if key in ignore_attrs:
                continue

            connection = connections.get(key)
            if not connection:
                missing_attrs.add(key)
                continue

            hierarchy = hierarchies[connection.source].copy()
            for name in connection.path:
                child = hierarchy[-1].get_node(name)
                if not child:
                    logger.debug(f'Missing node "{name}" in workflow {hierarchy[-1].name}')
                    break
                hierarchy.append(child)
            else:  # This else is run if there was no break in the for loop
                child = hierarchy.pop(-1)
                self.connect_attr(hierarchy, child, connection.attr, nodehierarchy, node, key)
                connected_attrs.add(key)
                continue

            missing_attrs.add(key)

        if missing_attrs:
            missing_attrs_str = p.join(sorted(missing_attrs))  # type: ignore[arg-type]
            logger.debug(f"Unable to find fMRIPrep outputs {missing_attrs_str} for workflow {nodehierarchy}")

        return connected_attrs
