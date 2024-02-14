# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from itertools import chain
from pathlib import Path
from zipfile import ZipFile

import nibabel as nib
import numpy as np
import pandas as pd
import scipy
from halfpipe.cli.commands.group_level.export import Statistic
from halfpipe.cli.parser import parse_args
from halfpipe.resource import get as get_resource
from halfpipe.stats.miscmaths import t2z_convert
from halfpipe.workflows.constants import Constants
from nilearn.image import new_img_like
from templateflow.api import get as get_template

from ....resource import setup as setup_test_resources


def test_group_level(tmp_path: Path) -> None:
    template_query = dict(
        template=Constants.reference_space,
        resolution=Constants.reference_res,
        desc="brain",
    )
    template_path = get_template(**template_query, suffix="T1w")
    template_mask_image_path = get_template(**template_query, suffix="mask")
    template_image = nib.nifti1.load(template_path)
    template_mask_image = nib.nifti1.load(template_mask_image_path)
    template_mask = np.asanyarray(template_mask_image.dataobj, dtype=bool)

    setup_test_resources()
    atlases_path = get_resource("atlases.zip")
    with ZipFile(atlases_path) as zip_file:
        zip_file.extractall(tmp_path)

    brainnetome_image_path = tmp_path / "atlas-Brainnetome_dseg.nii.gz"
    brainnetome_labels_path = tmp_path / "atlas-Brainnetome_dseg.txt"

    random_number_generator = np.random.default_rng()

    subjects: list[int] = list()
    z_values: list[float] = list()
    r_squared_values: list[float] = list()
    cohens_d_values: list[float] = list()

    effect_values = [0.5, 1, 2]
    dof = 99

    simulation_path = tmp_path / "derivatives"
    simulation_path.mkdir(parents=True)
    for i, beta in enumerate(effect_values, start=1):
        regressor = scipy.stats.zscore(random_number_generator.standard_normal(dof + 1))
        noise = scipy.stats.zscore(random_number_generator.standard_normal(dof + 1))
        linear_regression = scipy.stats.linregress(regressor, noise)
        noise = scipy.stats.zscore(noise - linear_regression.slope * regressor)

        variable = beta * regressor + noise

        linear_regression = scipy.stats.linregress(regressor, variable)
        assert np.isclose(linear_regression.intercept, 0, atol=1e-3)
        effect = linear_regression.slope
        assert np.isclose(effect, beta, atol=1e-3)

        residuals = variable - linear_regression.slope * regressor

        subjects.append(i)
        variance = np.square(linear_regression.stderr)
        t = effect / np.sqrt(variance)
        z = t2z_convert(t, dof)
        sigmasquareds = np.var(residuals)

        z_values.append(z)
        r_squared_values.append(np.square(linear_regression.rvalue))
        cohens_d_values.append(t / np.sqrt(dof - 1))

        statistics = dict(
            effect=effect,
            variance=variance,
            dof=dof,
            z=z,
            sigmasquareds=sigmasquareds,
        )

        prefix = str(simulation_path / f"sub-{i:02d}_taskcontrast-wmLoadVsControl")
        for statistic, value in statistics.items():
            array = np.full(template_mask.shape, np.nan)
            array[template_mask] = value
            image = new_img_like(template_image, array)
            nib.loadsave.save(image, f"{prefix}_stat-{statistic}_statmap.nii.gz")
        nib.loadsave.save(template_mask_image, f"{prefix}_mask.nii.gz")

    export_arguments = chain.from_iterable(
        (
            [
                "--export-atlas",
                "atlas-Brainnetome",
                statistic.name,
                str(brainnetome_image_path),
                str(brainnetome_labels_path),
            ]
            for statistic in Statistic
        )
    )
    opts, should_run = parse_args(
        argv=[
            "--n-procs",
            "1",
            "group-level",
            "--workdir",
            str(simulation_path),
            *export_arguments,
        ]
    )
    assert should_run
    action = getattr(opts, "action", None)
    assert action is not None
    action(opts)

    phenotypes_frame = pd.read_table(simulation_path / "phenotypes.tsv", index_col=0)
    phenotypes_frame = phenotypes_frame.loc[subjects, :]

    column_prefix = "taskcontrast-wmLoadVsControl_atlas-Brainnetome_label-A10lL_stat-"
    assert np.allclose(phenotypes_frame[f"{column_prefix}z"], z_values, atol=1e-3)
    assert np.allclose(phenotypes_frame[f"{column_prefix}effect"], effect_values, atol=1e-3)
    assert np.allclose(phenotypes_frame[f"{column_prefix}cohensD"], cohens_d_values, atol=1e-3)
    assert np.allclose(
        phenotypes_frame[f"{column_prefix}standardizedEffect"],
        np.sqrt(r_squared_values),
        atol=1e-2,
    )
