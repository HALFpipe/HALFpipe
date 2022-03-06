# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

from fmriprep import config
from nipype.algorithms import confounds as nac
from nipype.interfaces import fsl
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from ...interfaces.imagemaths.mask_coverage import MaskCoverage
from ...interfaces.imagemaths.resample import Resample
from ...interfaces.report.vals import CalcMean
from ...interfaces.resultdict.datasink import ResultdictDatasink
from ...interfaces.resultdict.make import MakeResultdicts
from ...interfaces.stats.dof import MakeDofVolume
from ...interfaces.utility.tsv import FillNA, MergeColumns
from ...utils.format import format_workflow
from ..constants import constants
from ..memory import MemoryCalculator


def _contrasts(design_file=None):
    import csv
    from pathlib import Path

    import numpy as np
    import pandas as pd

    from halfpipe.ingest.spreadsheet import read_spreadsheet

    design_df = read_spreadsheet(design_file)
    _, n = design_df.shape

    contrast_mat = np.zeros((1, n))
    contrast_mat[0, 0] = 1

    contrast_df = pd.DataFrame(
        contrast_mat, index=[design_df.columns[0]], columns=design_df.columns
    )

    out_with_header = Path.cwd() / "merge_with_header.tsv"
    contrast_df.to_csv(
        out_with_header,
        sep="\t",
        index=True,
        na_rep="n/a",
        header=True,
        quoting=csv.QUOTE_NONNUMERIC,
    )
    out_no_header = Path.cwd() / "merge_no_header.tsv"
    contrast_df.to_csv(out_no_header, sep="\t", index=False, na_rep="n/a", header=False)
    return str(out_with_header), str(out_no_header)


def init_seedbasedconnectivity_wf(
    workdir: str | Path,
    feature=None,
    seed_files=None,
    seed_spaces=None,
    memcalc=MemoryCalculator.default(),
):
    """
    create workflow to calculate seed connectivity maps
    """
    if feature is not None:
        name = f"{format_workflow(feature.name)}_wf"
    else:
        name = "seedbasedconnectivity_wf"
    workflow = pe.Workflow(name=name)

    # input
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "tags",
                "vals",
                "metadata",
                "bold",
                "mask",
                "confounds_selected",
                "seed_names",
                "seed_files",
                "seed_spaces",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["resultdicts"]), name="outputnode"
    )

    min_seed_coverage = 1
    if feature is not None:
        inputnode.inputs.seed_names = feature.seeds
        if hasattr(feature, "min_seed_coverage"):
            min_seed_coverage = feature.min_seed_coverage

    if seed_files is not None:
        inputnode.inputs.seed_files = seed_files

    if seed_spaces is not None:
        inputnode.inputs.seed_spaces = seed_spaces

    #
    statmaps = ["effect", "variance", "z", "dof", "mask"]
    make_resultdicts = pe.Node(
        MakeResultdicts(
            tagkeys=["feature", "seed"],
            imagekeys=[*statmaps, "design_matrix", "contrast_matrix"],
            metadatakeys=["mean_seed_tsnr", "coverage"],
        ),
        name="make_resultdicts",
    )
    if feature is not None:
        make_resultdicts.inputs.feature = feature.name
    workflow.connect(inputnode, "tags", make_resultdicts, "tags")
    workflow.connect(inputnode, "vals", make_resultdicts, "vals")
    workflow.connect(inputnode, "metadata", make_resultdicts, "metadata")
    workflow.connect(inputnode, "mask", make_resultdicts, "mask")

    workflow.connect(make_resultdicts, "resultdicts", outputnode, "resultdicts")

    #
    resultdict_datasink = pe.Node(
        ResultdictDatasink(base_directory=workdir), name="resultdict_datasink"
    )
    workflow.connect(make_resultdicts, "resultdicts", resultdict_datasink, "indicts")

    #
    reference_dict = dict(
        reference_space=constants.reference_space, reference_res=constants.reference_res
    )
    resample = pe.MapNode(
        Resample(interpolation="MultiLabel", **reference_dict),
        name="resample",
        iterfield=["input_image", "input_space"],
        n_procs=config.nipype.omp_nthreads,
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "seed_files", resample, "input_image")
    workflow.connect(inputnode, "seed_spaces", resample, "input_space")

    # Delete zero voxels for the seeds
    maskseeds = pe.Node(
        MaskCoverage(keys=["names"], min_coverage=min_seed_coverage),
        name="maskseeds",
        mem_gb=memcalc.volume_std_gb,
    )
    workflow.connect(inputnode, "mask", maskseeds, "mask_file")

    workflow.connect(inputnode, "seed_names", maskseeds, "names")
    workflow.connect(resample, "output_image", maskseeds, "in_files")

    workflow.connect(maskseeds, "names", make_resultdicts, "seed")
    workflow.connect(maskseeds, "coverage", make_resultdicts, "coverage")

    # calculate the mean time series of the region defined by each mask
    meants = pe.MapNode(
        fsl.ImageMeants(),
        name="meants",
        iterfield="mask",
        mem_gb=memcalc.series_std_gb,
    )
    workflow.connect(inputnode, "bold", meants, "in_file")
    workflow.connect(maskseeds, "out_files", meants, "mask")

    #
    design = pe.MapNode(
        MergeColumns(2), iterfield=["in1", "column_names1"], name="design"
    )
    workflow.connect(meants, "out_file", design, "in1")
    workflow.connect(maskseeds, "names", design, "column_names1")
    workflow.connect(inputnode, "confounds_selected", design, "in2")

    workflow.connect(design, "out_with_header", make_resultdicts, "design_matrix")

    contrasts = pe.MapNode(
        niu.Function(
            input_names=["design_file"],
            output_names=["out_with_header", "out_no_header"],
            function=_contrasts,
        ),
        iterfield="design_file",
        name="contrasts",
    )
    workflow.connect(design, "out_with_header", contrasts, "design_file")

    workflow.connect(contrasts, "out_with_header", make_resultdicts, "contrast_matrix")

    fillna = pe.MapNode(FillNA(), iterfield="in_tsv", name="fillna")
    workflow.connect(design, "out_no_header", fillna, "in_tsv")

    # calculate the regression of the mean time series
    # onto the functional image.
    # the result is the seed connectivity map
    glm = pe.MapNode(
        fsl.GLM(
            out_file="beta.nii.gz",
            out_cope="cope.nii.gz",
            out_varcb_name="varcope.nii.gz",
            out_z_name="zstat.nii.gz",
            demean=True,
        ),
        name="glm",
        iterfield=["design", "contrasts"],
        mem_gb=memcalc.series_std_gb * 5,
    )
    workflow.connect(inputnode, "bold", glm, "in_file")
    workflow.connect(inputnode, "mask", glm, "mask")
    workflow.connect(fillna, "out_no_header", glm, "design")
    workflow.connect(contrasts, "out_no_header", glm, "contrasts")

    # make dof volume
    makedofvolume = pe.MapNode(
        MakeDofVolume(), iterfield=["design"], name="makedofvolume"
    )
    workflow.connect(inputnode, "bold", makedofvolume, "bold_file")
    workflow.connect(fillna, "out_no_header", makedofvolume, "design")

    workflow.connect(glm, "out_cope", make_resultdicts, "effect")
    workflow.connect(glm, "out_varcb", make_resultdicts, "variance")
    workflow.connect(glm, "out_z", make_resultdicts, "z")
    workflow.connect(makedofvolume, "out_file", make_resultdicts, "dof")

    #
    tsnr = pe.Node(nac.TSNR(), name="tsnr", mem_gb=2 * memcalc.series_std_gb)
    workflow.connect(inputnode, "bold", tsnr, "in_file")

    calcmean = pe.MapNode(
        CalcMean(), iterfield="mask", name="calcmean", mem_gb=memcalc.series_std_gb
    )
    workflow.connect(maskseeds, "out_files", calcmean, "mask")
    workflow.connect(tsnr, "tsnr_file", calcmean, "in_file")

    workflow.connect(calcmean, "mean", make_resultdicts, "mean_seed_tsnr")

    return workflow
