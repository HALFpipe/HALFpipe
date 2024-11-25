# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from templateflow.api import get as get_template

from halfpipe.ingest.events import ConditionFile
from halfpipe.model.feature import FeatureSchema
from halfpipe.model.file.base import File
from halfpipe.model.file.schema import FileSchema
from halfpipe.model.setting import SettingSchema
from halfpipe.model.spec import Spec, SpecSchema
from halfpipe.resource import get as get_resource


@dataclass
class TestSetting:
    name: str
    base_setting: dict[str, Any]


def make_spec(
    dataset_files: list[File],
    pcc_mask: Path,
    event_file: File | None = None,
    test_settings: list[TestSetting] | None = None,
) -> Spec:
    if test_settings is None:
        test_settings = [
            TestSetting(
                name="default",
                base_setting=dict(
                    confounds_removal=["(trans|rot)_[xyz]"],
                    grand_mean_scaling=dict(mean=10000.0),
                    ica_aroma=True,
                ),
            )
        ]

    spec_schema = SpecSchema()
    spec = spec_schema.load(spec_schema.dump(dict()), partial=True)  # get defaults
    assert isinstance(spec, Spec)

    # Set up files
    spec.files.extend(dataset_files)
    if event_file is not None:
        spec.files.append(event_file)

    file_schema = FileSchema()
    map_file = file_schema.load(
        dict(
            datatype="ref",
            suffix="map",
            extension=".nii.gz",
            tags=dict(desc="smith09"),
            path=str(get_resource("PNAS_Smith09_rsn10.nii.gz")),
            metadata=dict(space="MNI152NLin6Asym"),
        )
    )
    seed_file = file_schema.load(
        dict(
            datatype="ref",
            suffix="seed",
            extension=".nii.gz",
            tags=dict(desc="pcc"),
            path=str(pcc_mask),
            metadata=dict(space="MNI152NLin6Asym"),
        )
    )
    atlas_file = file_schema.load(
        dict(
            datatype="ref",
            suffix="atlas",
            extension=".nii.gz",
            tags=dict(desc="schaefer2018"),
            path=str(
                get_template(
                    "MNI152NLin2009cAsym",
                    resolution=2,
                    atlas="Schaefer2018",
                    desc="400Parcels17Networks",
                    suffix="dseg",
                )
            ),
            metadata=dict(space="MNI152NLin2009cAsym"),
        )
    )
    spec.files.append(map_file)
    spec.files.append(seed_file)
    spec.files.append(atlas_file)

    # Set up settings and features
    for test_setting in test_settings:
        add_settings_and_features_to_spec(spec, test_setting, event_file)

    return spec


def add_settings_and_features_to_spec(spec: Spec, test_setting: TestSetting, event_file: File | None) -> None:
    setting_schema = SettingSchema()
    name = test_setting.name
    base_setting = test_setting.base_setting
    glm_setting = setting_schema.load(
        dict(
            name=f"{name}DualRegAndSeedCorrAndTaskBasedSetting",
            output_image=True,  # TODO parametrize this
            bandpass_filter=dict(type="gaussian", hp_width=125.0),
            smoothing=dict(fwhm=6.0),
            **base_setting,
        )
    )
    falff_reho_corr_matrix_setting = setting_schema.load(
        dict(
            name=f"{name}FALFFAndReHoAndCorrMatrixSetting",
            output_image=False,
            bandpass_filter=dict(type="frequency_based", low=0.01, high=0.1),
            **base_setting,
        )
    )
    falff_unfiltered_setting = setting_schema.load(
        dict(
            name=f"{name}FALFFUnfilteredSetting",
            output_image=False,
            **base_setting,
        )
    )
    spec.settings.append(glm_setting)
    spec.settings.append(falff_reho_corr_matrix_setting)
    spec.settings.append(falff_unfiltered_setting)

    # Set up features
    feature_schema = FeatureSchema()
    if event_file is not None:
        conditions = ConditionFile(event_file).conditions
        contrast_values = {
            conditions[0]: 1.0,
            conditions[1]: -1.0,
        }
        task_based_feature = feature_schema.load(
            dict(
                name=f"{name}TaskBased",
                type="task_based",
                high_pass_filter_cutoff=125.0,
                conditions=conditions,
                contrasts=[
                    dict(name="contrast", type="t", values=contrast_values),
                ],
                setting=f"{name}DualRegAndSeedCorrAndTaskBasedSetting",
            )
        )
        spec.features.append(task_based_feature)
    pcc_feature = feature_schema.load(
        dict(
            name=f"{name}SeedCorr",
            type="seed_based_connectivity",
            seeds=["pcc"],
            setting=f"{name}DualRegAndSeedCorrAndTaskBasedSetting",
        ),
    )
    dual_feature = feature_schema.load(
        dict(
            name=f"{name}DualReg",
            type="dual_regression",
            maps=["smith09"],
            setting=f"{name}DualRegAndSeedCorrAndTaskBasedSetting",
        ),
    )
    fc_connectivity_feature = feature_schema.load(
        dict(
            name=f"{name}CorrMatrix",
            type="atlas_based_connectivity",
            atlases=["schaefer2018"],
            setting=f"{name}FALFFAndReHoAndCorrMatrixSetting",
        ),
    )
    reho_feature = feature_schema.load(
        dict(
            name=f"{name}ReHo",
            type="reho",
            setting=f"{name}FALFFAndReHoAndCorrMatrixSetting",
            smoothing=dict(fwhm=6.0),
        ),
    )
    falff_feature = feature_schema.load(
        dict(
            name=f"{name}FALFF",
            type="falff",
            setting=f"{name}FALFFAndReHoAndCorrMatrixSetting",
            unfiltered_setting=f"{name}FALFFUnfilteredSetting",
            smoothing=dict(fwhm=6.0),
        ),
    )
    spec.features.append(dual_feature)
    spec.features.append(pcc_feature)
    spec.features.append(fc_connectivity_feature)
    spec.features.append(reho_feature)
    spec.features.append(falff_feature)
