# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from argparse import Namespace
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property, partial
from pathlib import Path
from typing import Callable, Mapping

import nibabel as nib
import numpy as np
import pandas as pd
import pint
from tqdm import tqdm

from ....collect.derivatives import find_derivatives_directories
from ....file_index.bids import BIDSIndex
from ....logging import logger
from ....model.tags.resultdict import resultdict_entities
from ....result.bids.base import make_bids_prefix
from ....utils.multiprocessing import Pool
from ....utils.nipype import run_workflow
from ....workflows.constants import constants
from ....workflows.features.jacobian import init_jacobian_wf
from .design import DesignBase

ureg = pint.UnitRegistry()


def apply_derived(
    arguments: Namespace,
    design_base: DesignBase,
):
    ImagingVariables(
        arguments,
        design_base,
    ).apply()
    apply_derived_variables(
        arguments.derived_variable,
        design_base,
    )
    variables_to_drop: list[str] | None = arguments.drop_variable
    if variables_to_drop is not None:
        for name in variables_to_drop:
            design_base.drop_variable(name)


def calculate_jacobian(
    task: tuple[str, Path],
) -> tuple[str, Path]:
    """
    Calculates the jacobian for a given subject and transform path using a nipype workflow.
    All files are save din the current directory.

    Args:
        task (tuple[str, Path]): A tuple containing the subject ID and the path to the transformation file.

    Returns:
        tuple[str, Path]: A tuple containing the subject ID and the path to the jacobian file.
    """
    subject, transform_path = task
    wf_directory = Path.cwd() / f"sub-{subject}_jacobian_wf"
    wf = init_jacobian_wf(
        transform_path,
    )
    wf.base_dir = wf_directory
    graph = run_workflow(wf)
    (scale_jacobian,) = [node for node in graph.nodes if node.name == "scale_jacobian"]
    jacobian_path = scale_jacobian.result.outputs.out_file
    return subject, jacobian_path


@dataclass
class ImagingVariables:
    arguments: Namespace
    design_base: DesignBase

    @property
    def n_procs(self) -> int:
        return self.arguments.nipype_n_procs

    @cached_property
    def fmriprep_derivatives(self) -> BIDSIndex:
        input_directories: list[str] = self.arguments.input_directory
        index = BIDSIndex()
        for input_directory_str in input_directories:
            input_directory = Path(input_directory_str)
            for derivatives_directory in find_derivatives_directories(
                "fmriprep",
                input_directory,
            ):
                index.put(derivatives_directory)

        return index

    @cached_property
    def jacobian_paths(self) -> dict[str, Path]:
        index = self.fmriprep_derivatives

        query = {
            "datatype": "anat",
            "from": "T1w",
            "to": "MNI152NLin2009cAsym",
            "mode": "image",
            "suffix": "xfm",
            "extension": ".h5",
        }
        transform_paths = index.get(**query)
        if transform_paths is None:
            raise ValueError(
                "Cannot calculate jacobian. No transforms found in the input directories"
            )

        tasks: dict[str, Path] = dict()
        for transform_path in transform_paths:
            subject = index.get_tag_value(transform_path, "sub")
            if subject is None:
                continue
            elif subject in tasks:
                logger.warning(
                    f"Subject {subject} has multiple transforms in the index"
                )
                continue
            tasks[subject] = transform_path

        with Pool(processes=self.n_procs) as pool:
            data: dict[str, Path] = dict(
                tqdm(
                    pool.imap_unordered(calculate_jacobian, tasks.items()),
                    total=len(tasks),
                    desc="calculating jacobians",
                    unit="subjects",
                )
            )

        return data

    def get_brain_mask_path(self, subject: str) -> Path:
        index = self.fmriprep_derivatives
        brain_mask_paths = index.get(
            datatype="anat",
            sub=subject,
            space=constants.reference_space,
            res=str(constants.reference_res),
            desc="brain",
            suffix="mask",
            extension=".nii.gz",
        )
        if brain_mask_paths is None:
            raise ValueError(f"No brain mask found in the index for subject {subject}")
        brain_mask_path = brain_mask_paths.pop()
        return brain_mask_path

    @cached_property
    def jacobian_stats(self) -> pd.DataFrame:
        data: dict[str, dict[str, float]] = defaultdict(dict)
        for subject, jacobian_path in tqdm(
            self.jacobian_paths.items(),
            desc="calculating jacobian stats",
            unit="subjects",
        ):
            brain_mask_image = nib.load(self.get_brain_mask_path(subject))
            brain_mask = np.asanyarray(brain_mask_image.dataobj, dtype=bool)

            jacobian_image = nib.load(jacobian_path)
            jacobian_data = jacobian_image.get_fdata()[brain_mask]

            data["jacobian_mean"][subject] = jacobian_data.mean()
            data["jacobian_variance"][subject] = jacobian_data.var()

        return pd.DataFrame(data)

    def apply_total_intracranial_volume(self) -> None:
        index = self.fmriprep_derivatives

        brain_mask_paths = index.get(
            datatype="anat",
            space=None,
            res=None,
            desc="brain",
            suffix="mask",
            extension=".nii.gz",
        )
        if brain_mask_paths is None:
            raise ValueError(
                "Cannot calculate `total_intracranial_volume`. No brain masks found in the index"
            )
        data: dict[str, float] = dict()
        for brain_mask_path in tqdm(
            brain_mask_paths,
            desc="calculating total intracranial volume",
            unit="subjects",
        ):
            subject = index.get_tag_value(brain_mask_path, "sub")
            if subject is None:
                continue

            brain_mask_image = nib.load(brain_mask_path)

            voxel_size = np.array(brain_mask_image.header.get_zooms()[:3]) * ureg.mm
            voxel_volume: pint.Quantity = np.prod(voxel_size)

            brain_mask = np.asanyarray(brain_mask_image.dataobj, dtype=bool)
            total_intracranial_volume = (
                np.count_nonzero(brain_mask) * voxel_volume
            ).m_as(ureg.milliliter)

            data[subject] = total_intracranial_volume

        self.design_base.add_variable(
            "total_intracranial_volume",
            pd.Series(data),
        )

    def apply_from_vals(self, name: str):
        data: dict[str | None, dict[str, float]] = defaultdict(dict)
        for result in self.design_base.results:
            vals = result["vals"]

            tags = {
                key: value
                for key, value in result["tags"].items()
                if key not in resultdict_entities
            }
            subject = tags.pop("sub")

            prefix = make_bids_prefix(tags)
            data[prefix][subject] = vals.get(name, np.nan)

        for prefix, values in data.items():
            self.design_base.add_variable(
                name,
                pd.Series(values),
                prefix=prefix,
            )

    def apply_from_jacobian(self, name: str) -> None:
        self.design_base.add_variable(
            name,
            self.jacobian_stats[name],
        )

    def apply_jacobian(self) -> None:
        for subject, path in self.jacobian_paths.items():
            self.design_base.results.append(
                {
                    "tags": {
                        "sub": subject,
                        "feature": "jacobian",
                    },
                    "images": {
                        "effect": path,
                        "mask": self.get_brain_mask_path(subject),
                    },
                    "metadata": {},
                    "vals": {},
                }
            )

    def apply(self) -> None:
        arguments = self.arguments
        variable_handlers: Mapping[str, Callable] = dict(
            fd_mean=partial(self.apply_from_vals, "fd_mean"),
            fd_perc=partial(self.apply_from_vals, "fd_perc"),
            mean_gm_tsnr=partial(self.apply_from_vals, "mean_gm_tsnr"),
            aroma_noise_frac=partial(self.apply_from_vals, "aroma_noise_frac"),
            total_intracranial_volume=self.apply_total_intracranial_volume,
            jacobian_mean=partial(self.apply_from_jacobian, "jacobian_mean"),
            jacobian_variance=partial(self.apply_from_jacobian, "jacobian_variance"),
        )
        if arguments.imaging_variable is not None:
            for variable in arguments.imaging_variable:
                variable_handlers[variable]()
        image_handlers: Mapping[str, Callable] = dict(
            jacobian=self.apply_jacobian,
        )
        if arguments.derived_image is not None:
            for image in arguments.derived_image:
                image_handlers[image]()
        self.design_base.filter_results()


def apply_derived_variables(
    derived_variables: list[tuple[str, str]] | None,
    design_base: DesignBase,
):
    if derived_variables is None:
        return
    if design_base.data_frame is None:
        raise ValueError("Design has no data frame")
    for derived_variable in derived_variables:
        name, expression = derived_variable
        design_base.data_frame.eval(f"{name} = ({expression})", inplace=True)
        # Add contrast for new variable
        design_base.add_variable(name)
