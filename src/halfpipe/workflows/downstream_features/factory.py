# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re
from collections import defaultdict
from typing import Any

from nipype.pipeline import engine as pe

from ...collect.events import collect_events
from ...collect.metadata import collect_metadata
from ...logging import logger
from ...model.downstream_feature import DownstreamFeatureSchema
from ...model.spec import Spec
from ..factory import Factory, FactoryContext
from ..memory import MemoryCalculator
from ..features.factory import FeatureFactory

from ..downstream_features.gradients import init_gradients_wf

inputnode_name = re.compile(r"(?P<prefix>[a-z]+_)?inputnode")


def _find_feature(
    feature_name: str, 
    spec: Spec
    ) -> dict[str, Any]:
    (feature,) = [feature for feature in spec.features if feature.name == feature_name]
    return setting


class DownstreamFeatureFactory(Factory):
    """ Class is reponsible for connecting downstream feature workflows up into rest of halfpipe."""
    # ALL ADAPTED FROM FEATURE FACTORY NOT TESTED
    def __init__(
        self, 
        ctx: FactoryContext, 
        feature_factory: FeatureFactory,
        ) -> None:

        super().__init__(ctx)

        self.feature_factory = feature_factory

        instance = DownstreamFeatureSchema()
        featurenames = set()
        for downstream_feature in self.ctx.spec.downstream_features:
            downstream_featuredict = instance.dump(downstream_feature)
            assert isinstance(downstream_featuredict, dict)
            for k, v in downstream_featuredict.items():
                if k.endswith("feature"):
                    featurenames.add(v)

        # filled in by .create()
        self.workflows: dict[str, list[list[pe.Workflow]]] = defaultdict(list)

    def has(
        self, 
        name: str
        ) -> bool:
        """ Checks if downstream_feature of given name is present in the spec file. """
        for downstream_feature in self.ctx.spec.downstream_features:
            if downstream_feature.name == name:
                return True
        return False
    
    def get(
        self, 
        feature_name: str, 
        *_: Any
        ) -> list[list[pe.Workflow]]:
        raise NotImplementedError()

    def create(
        self, 
        source_file, 
        feature, 
        raw_sources: list | None = None
        ) -> pe.Workflow | None:
        """ Creates a downstream_feature workflow and connects it with HALFpipe."""
        # TODO add note about confounds action
        # for some features add confounds to design matrix
        # for some add seperate step 

        raw_sources = [] if raw_sources is None else raw_sources
        hierarchy = self._get_hierarchy("features_wf", source_file=source_file)
        parent_workflow = hierarchy[-1]

        database = self.ctx.database

        memcalc = MemoryCalculator.from_bold_file(source_file)
        kwargs: dict[str, Any] = dict(feature=feature, workdir=str(self.ctx.workdir), memcalc=memcalc)

        setting = _find_setting(feature.setting, self.ctx.spec)
        kwargs["space"] = setting["space"]

        # Prepare/load files necessary for type of feature workflow & create worklow
        # Necessary for anything in spec file that is a path/pointer
        if feature.type == "gradients":
            # TODO gradient reference

            workflow = init_gradients_wf(**kwargs)

        else:
            raise ValueError(f'Unknown feature type "{feature.type}"')

        # add workflow to larger halfpipe workflow
        parent_workflow.add_nodes([workflow])
        # hierarchy used in nested workflows
        hierarchy.append(workflow)

        self.workflows[feature.name].append(hierarchy)

        # TODO refactor
        for node in workflow._graph.nodes:
            m = inputnode_name.fullmatch(node.name)
            # only runs for input nodes
            if m is not None:
                # TODO why isnt this in a standard fetching

                # could be seperate method "connect input node"
                # look at input node and set inputs since we know them
                # overall getting correct inputs for node
                if hasattr(node.inputs, "repetition_time"):
                    database.fillmetadata("repetition_time", [source_file])
                    node.inputs.repetition_time = database.metadata(source_file, "repetition_time")
                
                # every workflow should have tags, potentially refactor
                if hasattr(node.inputs, "tags"):
                    node.inputs.tags = database.tags(source_file)

                # setting is preprocessing pipeline settings
                setting_name_field = "setting"
                prefix = m.group("prefix")
                if prefix is not None:
                    setting_name_field = f"{prefix}{setting_name_field}"

                setting_name = getattr(feature, setting_name_field)
                # this object has (dictionary?) w preprocessing settings
                setting = _find_setting(setting_name, self.ctx.spec)

                # not sure if all nodes have metadata (always connect it as input?)
                if hasattr(node.inputs, "metadata"):
                    metadata = collect_metadata(database, source_file, setting)
                    metadata["raw_sources"] = sorted(raw_sources)
                    node.inputs.metadata = metadata

                # looks for overlapping output node input node pairs and connect them (based on names of attributes - input node fields)
                # from halfpipe preprocessing
                self.post_processing_factory.connect(
                    hierarchy,
                    node,
                    source_file,
                    setting_name,
                    confounds_action=confounds_action,
                )
                # from fmriprep
                self.fmriprep_factory.connect(
                    hierarchy,
                    node,
                    source_file=source_file,
                    ignore_attrs=frozenset({"vals"}),
                )
                # TODO add new from feature factory (NEEDED FOR GRADIENTS)
                # first wf to take as input other feature

        return workflow
    
    def setup(self, raw_sources_dict: dict | None = None):
        raw_sources_dict = dict() if raw_sources_dict is None else raw_sources_dict

        for feature in self.ctx.spec.features:
            source_files = set(raw_sources_dict.keys())

            setting = _find_setting(feature.setting, self.ctx.spec)

            filters = setting.get("filters")
            if filters is not None and len(filters) > 0:
                source_files = self.ctx.database.applyfilters(source_files, filters)

            for source_file in source_files:
                source_file_raw_sources = raw_sources_dict[source_file]
                self.create(source_file, feature, raw_sources=source_file_raw_sources)

    # Needs to be implemented for gradients
    def connect(self, *args, **kwargs):
        raise NotImplementedError()
        # see base method