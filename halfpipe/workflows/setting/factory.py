# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from abc import abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple, NamedTuple, Hashable

from math import isclose

from nipype.pipeline import engine as pe

from .fmriprepadapter import init_fmriprep_adapter_wf
from .icaaroma import init_ica_aroma_components_wf, init_ica_aroma_regression_wf
from .smoothing import init_smoothing_wf
from .grand_mean_scaling import init_grand_mean_scaling_wf
from .bandpassfilter import init_bandpass_filter_wf
from .confounds import init_confounds_select_wf, init_confounds_regression_wf
from .settingadapter import init_setting_adapter_wf
from .output import init_setting_output_wf

from ...ingest.collect import collect_metadata
from ..factory import Factory
from ..bypass import init_bypass_wf
from ..resampling.factory import AltBOLDFactory
from ..memory import MemoryCalculator, patch_mem_gb

from ...utils.copy import deepcopyfactory
from ...utils.hash import b32_digest
from ...utils import logger

alphabet = "abcdefghijklmnopqrstuvwxzy"


class SettingTuple(NamedTuple):
    value: Hashable | None
    suffix: str | None


class LookupTuple(NamedTuple):
    setting_tuple: SettingTuple
    memcalc: MemoryCalculator


class ICAAROMAComponentsFactory(Factory):
    def __init__(self, ctx, fmriprep_factory, alt_bold_factory):
        super(ICAAROMAComponentsFactory, self).__init__(ctx)

        self.alt_bold_factory = alt_bold_factory
        self.fmriprep_factory = fmriprep_factory

    def setup(self):
        prototype = init_ica_aroma_components_wf(workdir=str(self.workdir))
        self.wf_name = prototype.name

    def get(self, sourcefile, **_):
        hierarchy = self._get_hierarchy("settings_wf", sourcefile=sourcefile)
        wf = hierarchy[-1]

        vwf = wf.get_node(self.wf_name)
        connect = False

        if vwf is None:
            connect = True

            memcalc = MemoryCalculator.from_bold_file(sourcefile)
            vwf = init_ica_aroma_components_wf(workdir=str(self.workdir), memcalc=memcalc)

            for node in vwf._get_all_nodes():
                patch_mem_gb(node, memcalc)

            wf.add_nodes([vwf])

        inputnode = vwf.get_node("inputnode")
        assert isinstance(inputnode, pe.Node)
        hierarchy.append(vwf)

        if connect:
            inputnode.inputs.tags = self.database.tags(sourcefile)
            self.database.fillmetadata("repetition_time", [sourcefile])
            inputnode.inputs.repetition_time = self.database.metadata(sourcefile, "repetition_time")
            self.alt_bold_factory.connect(hierarchy, inputnode, sourcefile=sourcefile)
            self.fmriprep_factory.connect(hierarchy, inputnode, sourcefile=sourcefile)

        outputnode = vwf.get_node("outputnode")

        return hierarchy, outputnode


class LookupFactory(Factory):
    def __init__(self, ctx, previous_factory: Factory):
        super(LookupFactory, self).__init__(ctx)

        self.wf_names: Dict[SettingTuple, str] = dict()
        self.wf_factories: Dict[LookupTuple, Callable] = dict()

        self.tpl_by_setting_name: Dict[str, SettingTuple] = dict()

        self.previous_factory = previous_factory

    def setup(self):
        setting_names = [setting["name"] for setting in self.spec.settings]

        previous_tpls = []

        newsuffix_by_prevtpl: Optional[Dict[Tuple, str]] = None

        if isinstance(self.previous_factory, LookupFactory):
            if len(self.previous_factory.tpl_by_setting_name) > 0:
                previous_tpls.extend(
                    set(self.previous_factory.tpl_by_setting_name.values())
                )

                # 2**16 values for suffix should be sufficient to avoid collisions
                newsuffixes = [b32_digest(tpl)[:4] for tpl in previous_tpls]

                newsuffix_by_prevtpl = dict(zip(previous_tpls, newsuffixes))

        suffixes = []
        for name in setting_names:
            suffix = None
            if isinstance(self.previous_factory, LookupFactory):
                if isinstance(newsuffix_by_prevtpl, dict):
                    suffix = newsuffix_by_prevtpl[
                        self.previous_factory.tpl_by_setting_name[name]
                    ]
            suffixes.append(suffix)

        tpls = map(self._tpl, self.spec.settings)

        self.tpl_by_setting_name = {
            setting_name: SettingTuple(tpl, suffix)
            for setting_name, tpl, suffix in zip(setting_names, tpls, suffixes)
        }

    @abstractmethod
    def _prototype(self, lookup_tuple) -> pe.Workflow:
        raise NotImplementedError()

    @abstractmethod
    def _tpl(self, setting) -> Hashable:
        raise NotImplementedError()

    def _should_skip(self, obj):
        return obj is None

    def _connect_inputs(self, hierarchy, inputnode, sourcefile, setting_name, _):
        if hasattr(inputnode.inputs, "repetition_time"):
            self.database.fillmetadata("repetition_time", [sourcefile])
            inputnode.inputs.repetition_time = self.database.metadata(sourcefile, "repetition_time")
        if hasattr(inputnode.inputs, "tags"):
            inputnode.inputs.tags = self.database.tags(sourcefile)
        self.previous_factory.connect(hierarchy, inputnode, sourcefile=sourcefile, setting_name=setting_name)

    def wf_factory(self, lookup_tuple: LookupTuple):
        if lookup_tuple not in self.wf_factories:
            logger.debug(f"Creating workflow with {self.__class__.__name__} for {lookup_tuple}")
            prototype = self._prototype(lookup_tuple)
            self.wf_factories[lookup_tuple] = deepcopyfactory(prototype)

            prototype_name = prototype.name
            assert isinstance(prototype_name, str)
            self.wf_names[lookup_tuple.setting_tuple] = prototype_name

        return self.wf_factories[lookup_tuple]()

    def get(self, sourcefile, setting_name):
        hierarchy = self._get_hierarchy("settings_wf", sourcefile=sourcefile)
        wf = hierarchy[-1]

        setting_tuple = self.tpl_by_setting_name[setting_name]
        lookup_tuple = LookupTuple(
            setting_tuple=setting_tuple,
            memcalc=MemoryCalculator.from_bold_file(sourcefile),
        )

        vwf = None
        if setting_tuple in self.wf_names:
            vwf = wf.get_node(self.wf_names[setting_tuple])
        connect_inputs = False

        if vwf is None:
            connect_inputs = True
            vwf = self.wf_factory(lookup_tuple)
            wf.add_nodes([vwf])

        inputnode = vwf.get_node("inputnode")
        hierarchy.append(vwf)

        if connect_inputs:
            self._connect_inputs(hierarchy, inputnode, sourcefile, setting_name, lookup_tuple)

        outputnode = vwf.get_node("outputnode")

        return hierarchy, outputnode


class FmriprepAdapterFactory(LookupFactory):
    def _prototype(self, lookup_tuple: LookupTuple) -> pe.Workflow:
        return init_fmriprep_adapter_wf(memcalc=lookup_tuple.memcalc)

    def _tpl(self, _) -> Hashable:
        return SettingTuple(value=None, suffix=None)


class SmoothingFactory(LookupFactory):
    def _prototype(self, lookup_tuple: LookupTuple) -> pe.Workflow:
        setting_tuple = lookup_tuple.setting_tuple
        suffix = setting_tuple.suffix
        fwhm = setting_tuple.value

        if fwhm is None or float(fwhm) <= 0 or isclose(float(fwhm), 0):
            return init_bypass_wf(attrs=["files", "mask", "vals"], name="no_smoothing_wf", suffix=suffix)

        return init_smoothing_wf(fwhm=fwhm, memcalc=lookup_tuple.memcalc, suffix=suffix)

    def _tpl(self, setting) -> Hashable:
        smoothing_dict = setting.get("smoothing")

        smoothing = None
        if isinstance(smoothing_dict, dict) and smoothing_dict.get("fwhm") is not None:
            fwhm = smoothing_dict["fwhm"]
            smoothing = f"{fwhm:f}"

        return smoothing


class GrandMeanScalingFactory(LookupFactory):
    def _prototype(self, lookup_tuple: LookupTuple) -> pe.Workflow:
        setting_tuple = lookup_tuple.setting_tuple
        suffix = setting_tuple.suffix
        mean = setting_tuple.value

        if mean is None:
            return init_bypass_wf(
                attrs=["files", "mask", "vals"],
                name="no_grand_mean_scaling_wf",
                suffix=suffix,
            )
        return init_grand_mean_scaling_wf(
            mean=mean, memcalc=lookup_tuple.memcalc, suffix=suffix
        )

    def _tpl(self, setting) -> Hashable:
        grand_mean_scaling_dict = setting.get("grand_mean_scaling")

        grand_mean_scaling = None
        if isinstance(grand_mean_scaling_dict, dict) and grand_mean_scaling_dict.get("mean") is not None:
            mean = grand_mean_scaling_dict["mean"]
            grand_mean_scaling = f"{mean:f}"

        return grand_mean_scaling


class ICAAROMARegressionFactory(LookupFactory):
    def __init__(self, ctx, previous_factory, ica_aroma_components_factory):
        super(ICAAROMARegressionFactory, self).__init__(ctx, previous_factory)
        self.ica_aroma_components_factory = ica_aroma_components_factory

    def _prototype(self, lookup_tuple: LookupTuple) -> pe.Workflow:
        setting_tuple = lookup_tuple.setting_tuple
        suffix = setting_tuple.suffix
        ica_aroma = setting_tuple.value

        if ica_aroma is not True:
            return init_bypass_wf(
                attrs=["files", "mask", "vals"],
                name="no_ica_aroma_regression_wf",
                suffix=suffix,
            )
        return init_ica_aroma_regression_wf(
            workdir=str(self.workdir),
            memcalc=lookup_tuple.memcalc,
            suffix=suffix,
        )

    def _tpl(self, setting) -> Hashable:
        ica_aroma = setting.get("ica_aroma") is True
        return ica_aroma

    def _connect_inputs(
        self, hierarchy, inputnode, sourcefile, setting_name, lookup_tuple: LookupTuple
    ):
        super(ICAAROMARegressionFactory, self)._connect_inputs(
            hierarchy, inputnode, sourcefile, setting_name, lookup_tuple
        )

        setting_tuple = lookup_tuple.setting_tuple
        ica_aroma = setting_tuple.value

        if ica_aroma is True:
            self.ica_aroma_components_factory.connect(
                hierarchy, inputnode, sourcefile=sourcefile, setting_name=setting_name
            )


class BandpassFilterFactory(LookupFactory):
    def _prototype(self, lookup_tuple: LookupTuple) -> pe.Workflow:
        setting_tuple = lookup_tuple.setting_tuple
        suffix = setting_tuple.suffix
        bandpass_filter = setting_tuple.value

        if bandpass_filter is None:
            return init_bypass_wf(
                attrs=["files", "mask", "vals"],
                name="no_bandpass_filter_wf",
                suffix=suffix,
            )
        return init_bandpass_filter_wf(
            bandpass_filter=bandpass_filter, memcalc=lookup_tuple.memcalc, suffix=suffix
        )

    def _tpl(self, setting) -> Hashable:
        bandpass_filter_dict = setting.get("bandpass_filter")

        bandpass_filter = None
        if isinstance(bandpass_filter_dict, dict) and bandpass_filter_dict.get("type") is not None:
            if bandpass_filter_dict.get("type") == "gaussian":
                if bandpass_filter_dict.get("lp_width") is not None or bandpass_filter_dict.get("hp_width") is not None:
                    bandpass_filter = (
                        "gaussian",
                        bandpass_filter_dict.get("lp_width"),
                        bandpass_filter_dict.get("hp_width")
                    )
            elif bandpass_filter_dict.get("type") == "frequency_based":
                if bandpass_filter_dict.get("low") is not None or bandpass_filter_dict.get("high") is not None:
                    bandpass_filter = (
                        "frequency_based",
                        bandpass_filter_dict.get("low"),
                        bandpass_filter_dict.get("high")
                    )

        return bandpass_filter


class SettingAdapterFactory(LookupFactory):
    def _prototype(self, lookup_tuple: LookupTuple) -> pe.Workflow:
        setting_tuple = lookup_tuple.setting_tuple
        suffix = setting_tuple.suffix

        return init_setting_adapter_wf(suffix=suffix)

    def _tpl(self, _) -> Hashable:
        return None


class ConfoundsSelectFactory(LookupFactory):
    def _prototype(self, lookup_tuple: LookupTuple) -> pe.Workflow:
        setting_tuple = lookup_tuple.setting_tuple
        suffix = setting_tuple.suffix
        confound_names = setting_tuple.value

        if confound_names is None:
            return init_bypass_wf(
                attrs=["bold", "confounds", "mask", "vals"],
                unconnected_attrs=["confounds_matrix"],
                name="no_confounds_select_wf",
                suffix=suffix
            )
        return init_confounds_select_wf(confound_names=list(confound_names), suffix=suffix)

    def _tpl(self, setting) -> Hashable:
        confounds_removal = setting.get("confounds_removal")

        confound_names = None
        if confounds_removal is not None and len(confounds_removal) > 0:
            confound_names = tuple(sorted(confounds_removal))

        return confound_names


class ConfoundsRegressionFactory(LookupFactory):
    def _prototype(self, lookup_tuple: LookupTuple) -> pe.Workflow:
        setting_tuple = lookup_tuple.setting_tuple
        suffix = setting_tuple.suffix
        has_confounds = setting_tuple.value

        if has_confounds is not True:
            return init_bypass_wf(
                attrs=["bold", "confounds_selected", "confounds", "mask", "vals"],
                name="no_confounds_regression_wf",
                suffix=suffix
            )
        return init_confounds_regression_wf(memcalc=lookup_tuple.memcalc, suffix=suffix)

    def _tpl(self, setting) -> Hashable:
        confounds_removal = setting.get("confounds_removal")

        has_confounds = False
        if confounds_removal is not None and len(confounds_removal) > 0:
            has_confounds = True

        return has_confounds


class SettingFactory(Factory):
    def __init__(self, ctx, fmriprep_factory):
        super(SettingFactory, self).__init__(ctx)

        self.fmriprep_factory = fmriprep_factory

        self.alt_bold_factory = AltBOLDFactory(ctx, self.fmriprep_factory)
        self.ica_aroma_components_factory = ICAAROMAComponentsFactory(ctx, self.fmriprep_factory, self.alt_bold_factory)
        self.fmriprep_adapter_factory = FmriprepAdapterFactory(ctx, self.fmriprep_factory)
        self.smoothing_factory = SmoothingFactory(ctx, self.fmriprep_adapter_factory)
        self.grand_mean_scaling_factory = GrandMeanScalingFactory(ctx, self.smoothing_factory)
        self.ica_aroma_regression_factory = ICAAROMARegressionFactory(ctx, self.grand_mean_scaling_factory, self.ica_aroma_components_factory)
        self.bandpass_filter_factory = BandpassFilterFactory(ctx, self.ica_aroma_regression_factory)

        self.setting_adapter_factory = SettingAdapterFactory(ctx, self.bandpass_filter_factory)
        self.confounds_select_factory = ConfoundsSelectFactory(ctx, self.setting_adapter_factory)
        self.confounds_regression_factory = ConfoundsRegressionFactory(ctx, self.confounds_select_factory)

        setting_names = set(setting["name"] for setting in self.spec.settings if setting.get("output_image") is True)
        self.sourcefiles = self.get_sourcefiles(setting_names)

    def get_sourcefiles(self, setting_names):
        filepaths = set(self.database.get(datatype="func", suffix="bold"))
        ret = set()
        for setting in self.spec.settings:
            if setting.get("name") in setting_names:
                filters = setting.get("filters")
                if filters is None or len(filters) == 0:
                    return filepaths
                else:
                    ret |= self.database.applyfilters(filepaths, filters)
        return ret

    def setup(self, raw_sources_dict=dict()):
        self.alt_bold_factory.setup()
        self.ica_aroma_components_factory.setup()
        self.fmriprep_adapter_factory.setup()
        self.smoothing_factory.setup()
        self.grand_mean_scaling_factory.setup()
        self.ica_aroma_regression_factory.setup()
        self.bandpass_filter_factory.setup()

        self.setting_adapter_factory.setup()
        self.confounds_select_factory.setup()
        self.confounds_regression_factory.setup()

        for setting in self.spec.settings:
            setting_output_wf_factory = deepcopyfactory(
                init_setting_output_wf(workdir=str(self.workdir), setting_name=setting["name"])
            )

            if setting.get("output_image") is not True:
                continue  # create lazily in FeatureFactory

            sourcefiles = set(raw_sources_dict.keys())

            filters = setting.get("filters")
            if filters is not None and len(filters) > 0:
                sourcefiles = self.database.applyfilters(sourcefiles, filters)

            for sourcefile in sourcefiles:
                hierarchy = self._get_hierarchy("settings_wf", sourcefile=sourcefile)

                wf = setting_output_wf_factory()
                hierarchy[-1].add_nodes([wf])
                hierarchy.append(wf)

                inputnode = wf.get_node("inputnode")

                tags = dict(setting=setting["name"])
                tags.update(self.database.tags(sourcefile))
                inputnode.inputs.tags = tags

                metadata = collect_metadata(self.database, sourcefile, setting)
                if raw_sources_dict.get(sourcefile) is not None:
                    metadata["raw_sources"] = raw_sources_dict.get(sourcefile)
                inputnode.inputs.metadata = metadata

                self.connect(
                    hierarchy,
                    inputnode,
                    sourcefile,
                    setting_name=setting["name"],
                    confounds_action="regression",
                )

    def get(self, sourcefile, setting_name, confounds_action=None):
        self.ica_aroma_components_factory.get(sourcefile)  # make sure ica aroma components are always calculated
        if confounds_action == "select":
            return self.confounds_select_factory.get(sourcefile, setting_name)
        elif confounds_action == "regression":
            return self.confounds_regression_factory.get(sourcefile, setting_name)
        elif confounds_action is None:
            return self.setting_adapter_factory.get(sourcefile, setting_name)
        else:
            raise ValueError(f"Unknown counfounds action '{confounds_action}'")
