# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from nipype.pipeline import engine as pe

from fmriprep import config
from fmriprep.cli.workflow import build_workflow

from .factory import Factory
from .report import init_anat_report_wf, init_func_report_wf
from .constants import constants

from ..utils import deepcopyfactory


def _find_input(hierarchy, node, attr):
    wf = hierarchy[-1]
    for u, _, datadict in wf._graph.in_edges(nbunch=node, data=True):
        for in_attr, out_attr in datadict["connect"]:
            if out_attr == attr:
                return hierarchy, u, in_attr
    raise ValueError()


def _find_child(hierarchy, name):
    wf = hierarchy[-1]
    for node in wf._graph.nodes():
        if node.name == name:
            return hierarchy, node
        elif isinstance(node, pe.Workflow):
            res = _find_child([*hierarchy, node], name)
            if res is not None:
                return res


class FmriprepFactory(Factory):
    def __init__(self, ctx):
        super(FmriprepFactory, self).__init__(ctx)

    def setup(self, workdir, boldfilepaths):
        spec = self.spec
        database = self.database
        bidsdatabase = self.bidsdatabase
        workflow = self.workflow
        uuidstr = str(workflow.uuid)[:8]
        bids_dir = Path(workdir) / "rawdata"

        # init fmriprep config
        output_dir = Path(workdir) / "derivatives"
        output_dir.mkdir(parents=True, exist_ok=True)

        fmriprep_dir = output_dir / "fmriprep"
        fmriprep_dir.mkdir(parents=True, exist_ok=True)

        subjects = set()
        bidssubjects = set()
        for boldfilepath in boldfilepaths:
            subject = database.tagval(boldfilepath, "sub")

            if subject is None:
                continue

            bidspath = bidsdatabase.tobids(boldfilepath)
            bidssubject = bidsdatabase.tagval(bidspath, "subject")

            if bidssubject is None:
                continue

            subjects.add(subject)
            bidssubjects.add(bidssubject)

        subjects = list(subjects)
        bidssubjects = list(bidssubjects)

        ignore = ["sbref"]
        if spec.global_settings["slice_timing"] is not True:
            ignore.append("slicetiming")

        skull_strip_t1w = {
            "none": "skip",
            "auto": "auto",
            "ants": "force",
        }[spec.global_settings["skull_strip_algorithm"]]

        config.from_dict(
            {
                "bids_dir": bids_dir,
                "output_dir": output_dir,
                "fmriprep_dir": fmriprep_dir,
                "output_layout": "legacy",
                "log_dir": str(workdir),
                "work_dir": str(workdir / ".fmriprep"),
                "participant_label": bidssubjects,
                "ignore": ignore,
                "use_aroma": False,
                "dummy_scans": 0,  # force user to take care of this manually
                "skull_strip_t1w": skull_strip_t1w,
                "anat_only": spec.global_settings["anat_only"],
                "write_graph": spec.global_settings["write_graph"],
                "hires": spec.global_settings["hires"],
                "run_reconall": spec.global_settings["run_reconall"],
                "cifti_output": False,  # we do this in halfpipe
                "t2s_coreg": spec.global_settings["t2s_coreg"],
                "medial_surface_nan": spec.global_settings["medial_surface_nan"],
                "output_spaces": f"{constants.reference_space}:res-{constants.reference_res}",
                "bold2t1w_dof": spec.global_settings["bold2t1w_dof"],
                "fmap_bspline": spec.global_settings["fmap_bspline"],
                "force_syn": spec.global_settings["force_syn"],
                "longitudinal": spec.global_settings["longitudinal"],
                "regressors_all_comps": spec.global_settings["regressors_all_comps"],
                "regressors_dvars_th": spec.global_settings["regressors_dvars_th"],
                "regressors_fd_th": spec.global_settings["regressors_fd_th"],
                "skull_strip_fixed_seed": spec.global_settings["skull_strip_fixed_seed"],
                "skull_strip_template": spec.global_settings["skull_strip_template"],
                "aroma_err_on_warn": spec.global_settings["aroma_err_on_warn"],
                "aroma_melodic_dim": spec.global_settings["aroma_melodic_dim"],
                "sloppy": spec.global_settings["sloppy"],
            }
        )
        nipype_dir = Path(workdir) / constants.workflowdir
        nipype_dir.mkdir(parents=True, exist_ok=True)
        config_file = nipype_dir / f"fmriprep.config.{uuidstr}.toml"
        config.to_filename(config_file)

        retval = dict()
        build_workflow(config_file, retval)
        fmriprep_wf = retval["workflow"]
        workflow.add_nodes([fmriprep_wf])

        # halfpipe-specific report workflows
        anat_report_wf_factory = deepcopyfactory(init_anat_report_wf(workdir=str(self.workdir), memcalc=self.memcalc))
        for subject_id in subjects:
            hierarchy = self._get_hierarchy("reports_wf", subject_id=subject_id)

            wf = anat_report_wf_factory()
            hierarchy[-1].add_nodes([wf])
            hierarchy.append(wf)

            inputnode = wf.get_node("inputnode")
            inputnode.inputs.tags = {
                "sub": subject_id
            }

            self.connect(hierarchy, inputnode, subject_id=subject_id)

        func_report_wf_factory = deepcopyfactory(init_func_report_wf(workdir=str(self.workdir), memcalc=self.memcalc))
        for boldfilepath in boldfilepaths:
            hierarchy = self._get_hierarchy("reports_wf", sourcefile=boldfilepath)

            wf = func_report_wf_factory()
            assert wf.name == "func_report_wf"  # check name for line 206
            hierarchy[-1].add_nodes([wf])
            hierarchy.append(wf)

            inputnode = wf.get_node("inputnode")
            inputnode.inputs.tags = database.tags(boldfilepath)
            inputnode.inputs.fd_thres = spec.global_settings["fd_thres"]

            self.connect(hierarchy, inputnode, sourcefile=boldfilepath)

    def connect(self, nodehierarchy, node, sourcefile=None, subject_id=None, **kwargs):
        """
        connect equally names attrs
        preferentially use datasinked outputs
        """

        _ = kwargs  # ignore kwargs

        connected_attrs = set()

        inputattrs = set(node.inputs.copyable_trait_names())
        dsattrs = set(attr for attr in inputattrs if attr.startswith("ds_"))

        def _connect(hierarchy):
            wf = hierarchy[-1]

            outputnode = wf.get_node("outputnode")
            outputattrs = set(outputnode.outputs.copyable_trait_names())
            attrs = (inputattrs & outputattrs) - connected_attrs  # find common attr names

            actually_connected_attrs = set()
            for _, _, datadict in wf._graph.in_edges(outputnode, data=True):
                _, infields = zip(*datadict.get("connect", []))
                actually_connected_attrs.update(infields)

            attrs &= actually_connected_attrs

            for attr in attrs:
                self.connect_attr(hierarchy, outputnode, attr, nodehierarchy, node, attr)
                connected_attrs.add(attr)

            while len(dsattrs) > 0:
                attr = dsattrs.pop()
                childtpl = _find_child(hierarchy, attr)
                if childtpl is not None:
                    childhierarchy, childnode = childtpl
                    childhierarchy, childnode, childattr = _find_input(
                        childhierarchy, childnode, "in_file"
                    )
                    self.connect_attr(
                        childhierarchy, childnode, childattr, nodehierarchy, node, attr
                    )
                    connected_attrs.add(attr)

        hierarchy = self._get_hierarchy("fmriprep_wf", sourcefile=sourcefile, subject_id=subject_id)

        wf = hierarchy[-1]

        # anat only
        anat_wf = wf.get_node("anat_preproc_wf")
        if anat_wf is None:
            # func first
            _connect(hierarchy)

            if "skip_vols" in inputattrs:
                initial_boldref_wf = wf.get_node("initial_boldref_wf")
                outputnode = initial_boldref_wf.get_node("outputnode")
                self.connect_attr([*hierarchy, initial_boldref_wf], outputnode, "skip_vols", nodehierarchy, node, "skip_vols")
                connected_attrs.add("skip_vols")

            for name in ["bold_bold_trans_wf", "bold_hmc_wf", "final_boldref_wf", "bold_reg_wf", "sdc_estimate_wf", "sdc_bypass_wf"]:
                bold_wf = wf.get_node(name)
                if bold_wf is not None:
                    _connect([*hierarchy, bold_wf])

            if "bold_split" in inputattrs:
                splitnode = wf.get_node("split_opt_comb")
                if splitnode is None:
                    splitnode = wf.get_node("bold_split")
                self.connect_attr(hierarchy, splitnode, "out_files", nodehierarchy, node, "bold_split")
                connected_attrs.add("bold_split")

            reporthierarchy = self._get_hierarchy("reports_wf", sourcefile=sourcefile, subject_id=subject_id)
            func_report_wf = reporthierarchy[-1].get_node("func_report_wf")  # this is not part of fmriprep
            if func_report_wf is not None:
                _connect([*reporthierarchy, func_report_wf])

            while wf.get_node("anat_preproc_wf") is None:
                hierarchy.pop()
                wf = hierarchy[-1]
            anat_wf = wf.get_node("anat_preproc_wf")
        anat_norm_wf = anat_wf.get_node("anat_norm_wf")
        _connect([*hierarchy, anat_wf, anat_norm_wf])
        _connect([*hierarchy, anat_wf])
        return
