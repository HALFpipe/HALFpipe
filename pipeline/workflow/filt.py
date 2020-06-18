# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import afni
from nipype.interfaces import fsl

from fmriprep.workflows.bold import init_bold_confs_wf
from niworkflows.interfaces.utils import JoinTSVColumns
from fmriprep import config

from .smooth import init_smooth_wf
from ..interface import SelectColumnsTSV, GrandMeanScaling

from .memory import MemoryCalculator
from ..utils import first, second, hexdigest
from ..ui.utils import forbidden_chars
from .utils import ConnectAttrlistHelper


in_attrs_from_anat_preproc_wf_direct = ["t1w_tpms", "t1w_mask"]
in_attrs_from_anat_preproc_wf_keyselect = ["anat2std_xfm"]
in_attrs_from_anat_preproc_wf = (
    in_attrs_from_anat_preproc_wf_direct + in_attrs_from_anat_preproc_wf_keyselect
)

in_attrs_from_func_preproc_wf_direct = [
    "movpar_file",
    "rmsd_file",
    "skip_vols",
    "nonaggr_denoised_file",
    "aroma_confounds",
]
in_attrs_from_func_preproc_wf_keyselect = [
    "bold_std",
    "bold_std_ref",
    "bold_mask_std",
]
in_attrs_from_func_preproc_wf = (
    in_attrs_from_func_preproc_wf_direct + in_attrs_from_func_preproc_wf_keyselect
)

connect_filt_wf_attrs_from_anat_preproc_wf = ConnectAttrlistHelper(
    in_attrs_from_anat_preproc_wf_direct,
    keyAttr="outputnode.template",
    keyVal=config.workflow.spaces.get_spaces()[0],
    keySelectAttrs=in_attrs_from_anat_preproc_wf_keyselect,
)
connect_filt_wf_attrs_from_func_preproc_wf = ConnectAttrlistHelper(
    in_attrs_from_func_preproc_wf_direct,
    keyAttr="inputnode.template",
    keyVal=config.workflow.spaces.get_spaces()[0],
    keySelectAttrs=in_attrs_from_func_preproc_wf_keyselect,
)


def get_repetition_time(dic):
    return dic.get("RepetitionTime")


def make_confoundsendpoint(prefix, workflow, boldfileendpoint, confoundnames, memcalc):
    inputnode = workflow.get_node("inputnode")

    bold_confounds_wf = init_bold_confs_wf(
        mem_gb=memcalc.series_std_gb,
        metadata={},
        regressors_all_comps=config.workflow.regressors_all_comps,
        regressors_fd_th=config.workflow.regressors_fd_th,
        regressors_dvars_th=config.workflow.regressors_dvars_th,
        name=f"{prefix}_bold_confounds_wf",
    )

    for nodepath in bold_confounds_wf.list_node_names():
        hierarchy = nodepath.split(".")
        nodename = hierarchy[-1]
        if nodename.startswith("ds_report"):
            node = bold_confounds_wf.get_node(nodepath)

            parentpath = ".".join(hierarchy[:-1])
            if parentpath == "":
                parent = bold_confounds_wf
            else:
                parent = bold_confounds_wf.get_node(parentpath)
            assert isinstance(parent, pe.Workflow)

            parent.remove_nodes([node])

    bold_confounds_wf.get_node("inputnode").inputs.t1_transform_flags = [False]
    workflow.connect(*boldfileendpoint, bold_confounds_wf, "inputnode.bold")
    workflow.connect(
        [
            (
                inputnode,
                bold_confounds_wf,
                [
                    ("bold_mask_std", "inputnode.bold_mask"),
                    ("skip_vols", "inputnode.skip_vols"),
                    ("t1w_tpms", "inputnode.t1w_tpms"),
                    ("t1w_mask", "inputnode.t1w_mask"),
                    ("movpar_file", "inputnode.movpar_file"),
                    ("rmsd_file", "inputnode.rmsd_file"),
                    ("anat2std_xfm", "inputnode.t1_bold_xform"),
                ],
            ),
            (
                inputnode,
                bold_confounds_wf,
                [
                    (("metadata", get_repetition_time), "acompcor.repetition_time"),
                    (("metadata", get_repetition_time), "tcompcor.repetition_time"),
                ],
            ),
        ]
    )

    joincolumns = pe.Node(
        JoinTSVColumns(),
        run_without_submitting=True,
        mem_gb=memcalc.min_gb,
        name=f"{prefix}joincolumns",
    )
    workflow.connect(bold_confounds_wf, "outputnode.confounds_file", joincolumns, "in_file")
    workflow.connect(inputnode, "aroma_confounds", joincolumns, "join_file")

    selectcolumns = pe.Node(
        SelectColumnsTSV(column_names=list(confoundnames), output_with_header=False),
        run_without_submitting=True,
        mem_gb=memcalc.min_gb,
        name=f"{prefix}selectcolumns",
    )
    workflow.connect(joincolumns, "out_file", selectcolumns, "in_file")

    selectcolumnswithheader = pe.Node(
        SelectColumnsTSV(column_names=list(confoundnames), output_with_header=True),
        run_without_submitting=True,
        mem_gb=memcalc.min_gb,
        name=f"{prefix}selectcolumnswithheader",
    )
    workflow.connect(joincolumns, "out_file", selectcolumnswithheader, "in_file")

    return ((selectcolumns, "out_file"), (selectcolumnswithheader, "out_file"))


def make_variant_bold_filt_wf_name(variant):
    tagdict = dict(variant)

    name = "filt"
    for key in sorted(tagdict):
        value = tagdict[key]
        if not isinstance(value, str) or forbidden_chars.search(value) is not None:
            value = hexdigest(value)
        name += f"_{key}_{value}"
    return name


def init_bold_filt_wf(variant=None, memcalc=MemoryCalculator()):
    assert variant is not None

    name = make_variant_bold_filt_wf_name(variant)

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[*in_attrs_from_func_preproc_wf, *in_attrs_from_anat_preproc_wf, "metadata"]
        ),
        name="inputnode",
    )
    workflow.add_nodes([inputnode])

    metadatanode = pe.Node(niu.IdentityInterface(fields=["repetition_time"]), name="metadatanode")
    workflow.connect(
        [(inputnode, metadatanode, [(("metadata", get_repetition_time), "repetition_time")])]
    )

    bandpass = None

    ortendpoint = None

    boldfileendpoint = (inputnode, "bold_std")

    tagdict = dict(variant)

    # smoothing is done first
    if "smoothed" in tagdict:
        fwhm = float(tagdict["smoothed"])
        smooth_workflow = init_smooth_wf(fwhm=fwhm)
        workflow.connect(inputnode, "bold_mask_std", smooth_workflow, "inputnode.mask_file")
        workflow.connect(*boldfileendpoint, smooth_workflow, "inputnode.in_file")
        boldfileendpoint = (smooth_workflow, "outputnode.out_file")

    if "grand_mean_scaled" in tagdict:
        grand_mean = tagdict["grand_mean_scaled"]
        assert isinstance(grand_mean, float)
        grandmeanscaling = pe.Node(
            interface=GrandMeanScaling(grand_mean=grand_mean), name="grandmeanscaling"
        )
        workflow.connect(*boldfileendpoint, grandmeanscaling, "in_file")
        workflow.connect(inputnode, "bold_mask_std", grandmeanscaling, "mask_file")
        boldfileendpoint = (grandmeanscaling, "out_file")

    need_to_add_mean = False
    boldfileendpoint_for_meanfunc = boldfileendpoint

    # if we use gaussian band-pass filtering, we cannot orthogonalize these regressors
    # with respect to the filter, as afni tproject doesn't support this filter type
    # as such we need to remove them before to not re-introduce filtered-out variance
    simultaneous_bandpass_and_ort = True
    if "band_pass_filtered" in tagdict:
        type = first(tagdict["band_pass_filtered"])
        if type == "gaussian":
            simultaneous_bandpass_and_ort = False

    confounds_to_remove_before_filtering = set(("aroma_motion_[0-9]+",))
    if (
        not simultaneous_bandpass_and_ort
        and "confounds_removed" in tagdict
        and not confounds_to_remove_before_filtering.isdisjoint(tagdict["confounds_removed"])
    ):
        confoundsremovedset = set(tagdict["confounds_removed"])
        preconfoundsremoved = confounds_to_remove_before_filtering & confoundsremovedset
        postconfoundsremoved = confoundsremovedset - confounds_to_remove_before_filtering
        if len(postconfoundsremoved) == 0:
            del tagdict["confounds_removed"]
        else:
            tagdict["confounds_removed"] = postconfoundsremoved

        ortendpoint, _ = make_confoundsendpoint(
            "pre", workflow, boldfileendpoint, list(preconfoundsremoved), memcalc
        )
        tproject = pe.Node(afni.TProject(polort=1, out_file="tproject.nii"), name="pretproject")
        workflow.connect(*boldfileendpoint, tproject, "in_file")
        workflow.connect(metadatanode, "repetition_time", tproject, "TR")
        workflow.connect(*ortendpoint, tproject, "ort")
        boldfileendpoint = (tproject, "out_file")
        need_to_add_mean = True

    if "band_pass_filtered" in tagdict:
        type = first(tagdict["band_pass_filtered"])
        if type == "frequency_based":
            bandpass = tagdict["band_pass_filtered"][1:]
        elif type == "gaussian":

            def calc_highpass_sigma(temporal_filter_width=None, repetition_time=None):
                highpass_sigma = temporal_filter_width / (2.0 * repetition_time)
                return highpass_sigma

            calchighpasssigma = pe.Node(
                interface=niu.Function(
                    input_names=["temporal_filter_width", "repetition_time"],
                    output_names=["highpass_sigma"],
                    function=calc_highpass_sigma,
                ),
                name="calchighpasssigma",
            )
            workflow.connect(metadatanode, "repetition_time", calchighpasssigma, "repetition_time")
            calchighpasssigma.inputs.temporal_filter_width = second(tagdict["band_pass_filtered"])
            highpass = pe.Node(fsl.TemporalFilter(), name="gaussianfilter")
            workflow.connect(calchighpasssigma, "highpass_sigma", highpass, "highpass_sigma")
            workflow.connect(*boldfileendpoint, highpass, "in_file")
            need_to_add_mean = True

    if "confounds_removed" in tagdict:
        confoundnames = tagdict["confounds_removed"]
        if len(confoundnames) > 0:
            ortendpoint, _ = make_confoundsendpoint(
                "post", workflow, boldfileendpoint, confoundnames, memcalc
            )

    if bandpass is not None or ortendpoint is not None:
        tproject = pe.Node(afni.TProject(polort=1, out_file="tproject.nii"), name="tproject")
        workflow.connect(*boldfileendpoint, tproject, "in_file")
        workflow.connect(metadatanode, "repetition_time", tproject, "TR")
        if bandpass is not None:
            tproject.inputs.bandpass = bandpass
        if ortendpoint is not None:
            workflow.connect(*ortendpoint, tproject, "ort")
        boldfileendpoint = (tproject, "out_file")
        need_to_add_mean = True

    if need_to_add_mean is True:
        meanfunc = pe.Node(
            interface=fsl.ImageMaths(op_string="-Tmean", suffix="_mean"), name="meanfunc"
        )
        workflow.connect(*boldfileendpoint_for_meanfunc, meanfunc, "in_file")
        addmean = pe.Node(interface=fsl.BinaryMaths(operation="add"), name="addmean")
        workflow.connect(*boldfileendpoint, addmean, "in_file")
        workflow.connect(meanfunc, "out_file", addmean, "operand_file")
        boldfileendpoint = (addmean, "out_file")

    applymask = pe.Node(interface=fsl.ApplyMask(), name="applymask", mem_gb=memcalc.volume_std_gb,)
    workflow.connect(*boldfileendpoint, applymask, "in_file")
    workflow.connect(inputnode, "bold_mask_std", applymask, "mask_file")
    boldfileendpoint = (applymask, "out_file")

    endpoints = [boldfileendpoint]  # boldfile is finished

    if "confounds_extract" in tagdict:  # last
        confoundnames = tagdict["confounds_extract"]
        confoundsextractendpoint, confoundsextractendpointwithheader = make_confoundsendpoint(
            "extract", workflow, boldfileendpoint, confoundnames, memcalc
        )
        endpoints.append(confoundsextractendpoint)
        endpoints.append(confoundsextractendpointwithheader)

    outnames = [f"out{i+1}" for i in range(len(endpoints))]

    outputnode = pe.Node(niu.IdentityInterface(fields=[*outnames, "mask_file"]), name="outputnode",)
    workflow.connect(inputnode, "bold_mask_std", outputnode, "mask_file")

    for outname, endpoint in zip(outnames, endpoints):
        workflow.connect(*endpoint, outputnode, outname)

    return workflow
