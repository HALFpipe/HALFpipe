# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from typing import Any, Dict

from ...ingest.collect import collect_events, collect_metadata
from ...model import FeatureSchema
from ...utils import logger
from ..factory import Factory
from ..memory import MemoryCalculator
from .atlasbasedconnectivity import init_atlasbasedconnectivity_wf
from .dualregression import init_dualregression_wf
from .falff import init_falff_wf
from .reho import init_reho_wf
from .seedbasedconnectivity import init_seedbasedconnectivity_wf
from .taskbased import init_taskbased_wf

inputnode_name = re.compile(r"(?P<prefix>[a-z]+_)?inputnode")


def _find_setting(setting_name, spec):
    (setting,) = [
        setting for setting in spec.settings if setting["name"] == setting_name
    ]
    return setting


class FeatureFactory(Factory):
    def __init__(self, ctx, setting_factory):
        super(FeatureFactory, self).__init__(ctx)

        self.setting_factory = setting_factory

        instance = FeatureSchema()
        settingnames = set()
        for feature in self.ctx.spec.features:
            featuredict = instance.dump(feature)
            assert isinstance(featuredict, dict)
            for k, v in featuredict.items():
                if k.endswith("setting"):
                    settingnames.add(v)
        self.source_files = self.setting_factory.get_source_files(settingnames)

    def has(self, name):
        for feature in self.ctx.spec.features:
            if feature.name == name:
                return True
        return False

    def setup(self, raw_sources_dict=dict()):
        self.wfs = dict()

        for feature in self.ctx.spec.features:
            source_files = set(raw_sources_dict.keys())

            setting = _find_setting(feature.setting, self.ctx.spec)

            filters = setting.get("filters")
            if filters is not None and len(filters) > 0:
                source_files = self.ctx.database.applyfilters(source_files, filters)

            for source_file in source_files:
                source_file_raw_sources = raw_sources_dict[source_file]
                self.create(source_file, feature, raw_sources=source_file_raw_sources)

    def create(self, source_file, feature, raw_sources=[]):
        hierarchy = self._get_hierarchy("features_wf", source_file=source_file)
        wf = hierarchy[-1]

        database = self.ctx.database

        vwf = None

        memcalc = MemoryCalculator.from_bold_file(source_file)
        kwargs: Dict[str, Any] = dict(
            feature=feature, workdir=str(self.ctx.workdir), memcalc=memcalc
        )
        if feature.type == "task_based":
            confounds_action = "select"

            condition_files = collect_events(database, source_file)

            if isinstance(condition_files, str):
                condition_file_paths = [condition_files]
            elif isinstance(condition_files, tuple):
                condition_files = list(condition_files)

                condition_file_paths, _ = zip(*condition_files)
                condition_file_paths = list(condition_file_paths)
            else:  # we did not find any condition files
                logger.warning(
                    f'Skipping feature "{feature.name}" for "{source_file}" '
                    "because no event files could be found"
                )
                return

            raw_sources = [*raw_sources, *condition_file_paths]

            condition_units = None
            condition_units_set = database.metadatavalset("units", condition_file_paths)
            if condition_units_set is not None:
                if len(condition_units_set) == 1:
                    (condition_units,) = condition_units_set
            if condition_units is None:
                condition_units = "secs"  # default value
            if condition_units == "seconds":
                condition_units = "secs"

            vwf = init_taskbased_wf(
                condition_files=condition_files,
                condition_units=condition_units,
                **kwargs,
            )
        elif feature.type == "seed_based_connectivity":
            confounds_action = "select"
            kwargs["seed_files"] = []
            for seed in feature.seeds:
                (seed_file,) = database.get(datatype="ref", suffix="seed", desc=seed)
                kwargs["seed_files"].append(seed_file)
            database.fillmetadata("space", kwargs["seed_files"])
            kwargs["seed_spaces"] = [
                database.metadata(seed_file, "space")
                for seed_file in kwargs["seed_files"]
            ]
            vwf = init_seedbasedconnectivity_wf(**kwargs)
        elif feature.type == "dual_regression":
            confounds_action = "select"
            kwargs["map_files"] = []
            for map in feature.maps:
                (map_file,) = database.get(datatype="ref", suffix="map", desc=map)
                kwargs["map_files"].append(map_file)
            database.fillmetadata("space", kwargs["map_files"])
            kwargs["map_spaces"] = [
                database.metadata(map_file, "space") for map_file in kwargs["map_files"]
            ]
            vwf = init_dualregression_wf(**kwargs)
        elif feature.type == "atlas_based_connectivity":
            confounds_action = "regression"
            kwargs["atlas_files"] = []
            for atlas in feature.atlases:
                (atlas_file,) = database.get(datatype="ref", suffix="atlas", desc=atlas)
                kwargs["atlas_files"].append(atlas_file)
            database.fillmetadata("space", kwargs["atlas_files"])
            kwargs["atlas_spaces"] = [
                database.metadata(atlas_file, "space")
                for atlas_file in kwargs["atlas_files"]
            ]
            vwf = init_atlasbasedconnectivity_wf(**kwargs)
        elif feature.type == "reho":
            confounds_action = "regression"
            vwf = init_reho_wf(**kwargs)
        elif feature.type == "falff":
            confounds_action = "regression"
            vwf = init_falff_wf(**kwargs)
        else:
            raise ValueError(f'Unknown feature type "{feature.type}"')

        wf.add_nodes([vwf])
        hierarchy.append(vwf)

        if feature.name not in self.wfs:
            self.wfs[feature.name] = []
        self.wfs[feature.name].append(hierarchy)

        for node in vwf._graph.nodes:
            m = inputnode_name.fullmatch(node.name)
            if m is not None:
                if hasattr(node.inputs, "repetition_time"):
                    database.fillmetadata("repetition_time", [source_file])
                    node.inputs.repetition_time = database.metadata(
                        source_file, "repetition_time"
                    )
                if hasattr(node.inputs, "tags"):
                    node.inputs.tags = database.tags(source_file)

                setting_name_field = "setting"
                prefix = m.group("prefix")
                if prefix is not None:
                    setting_name_field = f"{prefix}{setting_name_field}"

                setting_name = getattr(feature, setting_name_field)
                setting = _find_setting(setting_name, self.ctx.spec)

                if hasattr(node.inputs, "metadata"):
                    metadata = collect_metadata(database, source_file, setting)
                    metadata["raw_sources"] = sorted(raw_sources)
                    node.inputs.metadata = metadata

                self.setting_factory.connect(
                    hierarchy,
                    node,
                    source_file,
                    setting_name,
                    confounds_action=confounds_action,
                )

        return vwf

    def get(self, feature_name, *_):
        return self.wfs[feature_name]

    def connect(self, *args, **kwargs):
        raise NotImplementedError()
