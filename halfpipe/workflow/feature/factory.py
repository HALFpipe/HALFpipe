# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re

from .atlasbasedconnectivity import init_atlasbasedconnectivity_wf
from .dualregression import init_dualregression_wf
from .falff import init_falff_wf
from .reho import init_reho_wf
from .seedbasedconnectivity import init_seedbasedconnectivity_wf
from .taskbased import init_taskbased_wf

from ..factory import Factory

from ...model import FeatureSchema

inputnode_name = re.compile(r"(?P<prefix>[a-z]+_)?inputnode")


class FeatureFactory(Factory):
    def __init__(self, ctx, setting_factory):
        super(FeatureFactory, self).__init__(ctx)

        self.setting_factory = setting_factory

        instance = FeatureSchema()
        settingnames = set()
        for feature in self.spec.features:
            featuredict = instance.dump(feature)
            for k, v in featuredict.items():
                if k.endswith("setting"):
                    settingnames.add(v)
        self.sourcefiles = self.setting_factory.get_sourcefiles(settingnames)

    def has(self, name):
        for feature in self.spec.features:
            if feature.name == name:
                return True
        return False

    def setup(self):
        self.wfs = dict()
        for sourcefile in self.sourcefiles:
            for feature in self.spec.features:
                self.create(sourcefile, feature)

    def create(self, sourcefile, feature):
        hierarchy = self._get_hierarchy("features_wf", sourcefile=sourcefile)
        wf = hierarchy[-1]

        database = self.database

        vwf = None
        kwargs = dict(feature=feature, workdir=self.workdir, memcalc=self.memcalc)
        if feature.type == "task_based":
            confounds_action = "select"
            condition_files = database.get_associations(sourcefile, datatype="func", suffix="events")
            condition_units = database.metadatavalset("units", condition_files)
            if len(condition_units) == 0:
                condition_units = "secs"
            else:
                condition_units, = condition_units
            if "txt" in database.get_tagval_set("extension", filepaths=condition_files):
                condition_files = [
                    (condition_file, database.get_tagval(condition_file, "condition"))
                    for condition_file in condition_files
                ]
            kwargs["condition_files"] = condition_files
            kwargs["condition_units"] = condition_units
            vwf = init_taskbased_wf(**kwargs)
        elif feature.type == "seed_based_connectivity":
            confounds_action = "select"
            kwargs["seed_files"] = []
            for seed in feature.seeds:
                (seed_file,) = database.get(datatype="ref", suffix="seed", desc=seed)
                kwargs["seed_files"].append(seed_file)
            database.fillmetadata("space", kwargs["seed_files"])
            kwargs["seed_spaces"] = [database.metadata(seed_file, "space") for seed_file in kwargs["seed_files"]]
            vwf = init_seedbasedconnectivity_wf(**kwargs)
        elif feature.type == "dual_regression":
            confounds_action = "select"
            kwargs["map_files"] = []
            for map in feature.maps:
                (map_file,) = database.get(datatype="ref", suffix="map", desc=map)
                kwargs["map_files"].append(map_file)
            database.fillmetadata("space", kwargs["map_files"])
            kwargs["map_spaces"] = [database.metadata(map_file, "space") for map_file in kwargs["map_files"]]
            vwf = init_dualregression_wf(**kwargs)
        elif feature.type == "atlas_based_connectivity":
            confounds_action = "regression"
            kwargs["atlas_files"] = []
            for atlas in feature.atlases:
                (atlas_file,) = database.get(datatype="ref", suffix="atlas", desc=atlas)
                kwargs["atlas_files"].append(atlas_file)
            database.fillmetadata("space", kwargs["atlas_files"])
            kwargs["atlas_spaces"] = [database.metadata(atlas_file, "space") for atlas_file in kwargs["atlas_files"]]
            vwf = init_atlasbasedconnectivity_wf(**kwargs)
        elif feature.type == "reho":
            confounds_action = "regression"
            vwf = init_reho_wf(**kwargs)
        elif feature.type == "falff":
            confounds_action = "regression"
            vwf = init_falff_wf(**kwargs)
        else:
            raise ValueError(f"Unknown feature type \"{feature.type}\"")

        wf.add_nodes([vwf])
        hierarchy.append(vwf)

        if feature.name not in self.wfs:
            self.wfs[feature.name] = []
        self.wfs[feature.name].append(hierarchy)

        for node in vwf._graph.nodes():
            m = inputnode_name.fullmatch(node.name)
            if m is not None:
                if hasattr(node.inputs, "repetition_time"):
                    database.fillmetadata("repetition_time", [sourcefile])
                    node.inputs.repetition_time = database.metadata(sourcefile, "repetition_time")
                if hasattr(node.inputs, "tags"):
                    node.inputs.tags = database.tags(sourcefile)
                settingnamefield = "setting"
                if m.group("prefix") is not None:
                    settingnamefield = f'{m.group("prefix")}{settingnamefield}'
                settingname = getattr(feature, settingnamefield)
                self.setting_factory.connect(hierarchy, node, sourcefile, settingname, confounds_action=confounds_action)

        return vwf

    def get(self, feature_name, **kwargs):
        return self.wfs[feature_name]

    def connect(self, *args, **kwargs):
        raise NotImplementedError()
