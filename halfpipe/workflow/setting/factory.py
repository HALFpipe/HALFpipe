# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import numpy as np

from .fmriprepadapter import init_fmriprep_adapter_wf
from .icaaroma import init_ica_aroma_components_wf, init_ica_aroma_regression_wf
from .smoothing import init_smoothing_wf
from .grandmeanscaling import init_grand_mean_scaling_wf
from .bandpassfilter import init_bandpass_filter_wf
from .confounds import init_confounds_select_wf, init_confounds_regression_wf
from .settingadapter import init_setting_adapter_wf
from .output import init_setting_output_wf

from ..factory import Factory
from ..bypass import init_bypass_wf

from ...utils import deepcopyfactory, b32digest

alphabet = "abcdefghijklmnopqrstuvwxzy"


class ICAAROMAComponentsFactory(Factory):
    def __init__(self, ctx, fmriprep_factory):
        super(ICAAROMAComponentsFactory, self).__init__(ctx)

        self.previous_factory = fmriprep_factory

    def setup(self):
        prototype = init_ica_aroma_components_wf(workdir=str(self.workdir), memcalc=self.memcalc)
        self.wf_name = prototype.name
        self.wf_factory = deepcopyfactory(prototype)

    def get(self, sourcefile, **kwargs):
        hierarchy = self._get_hierarchy("settings_wf", sourcefile=sourcefile)
        wf = hierarchy[-1]

        vwf = wf.get_node(self.wf_name)
        connect = False

        if vwf is None:
            connect = True
            vwf = self.wf_factory()
            wf.add_nodes([vwf])

        inputnode = vwf.get_node("inputnode")
        hierarchy.append(vwf)

        if connect:
            inputnode.inputs.tags = self.database.tags(sourcefile)
            self.database.fillmetadata("repetition_time", [sourcefile])
            inputnode.inputs.repetition_time = self.database.metadata(sourcefile, "repetition_time")
            self.previous_factory.connect(hierarchy, inputnode, sourcefile=sourcefile)

        outputnode = vwf.get_node("outputnode")

        return hierarchy, outputnode


class LookupFactory(Factory):
    def __init__(self, ctx, previous_factory):
        super(LookupFactory, self).__init__(ctx)

        self.previous_factory = previous_factory

    def setup(self):
        settingnames = [setting["name"] for setting in self.spec.settings]

        prevtpls = []

        if hasattr(self.previous_factory, "by_settingname"):
            prevtpls.extend(set(self.previous_factory.by_settingname.values()))

            # 2**16 values for suffix should be sufficient to avoid collisions
            newsuffixes = [b32digest(tpl)[:4] for tpl in prevtpls]

            newsuffix_by_prevtpl = dict(zip(prevtpls, newsuffixes))

        suffixes = []
        for name in settingnames:
            suffix = None
            if len(prevtpls) > 1:
                suffix = newsuffix_by_prevtpl[self.previous_factory.by_settingname[name]]
            suffixes.append(suffix)

        tpls = map(self._tpl, self.spec.settings)

        self.by_settingname = dict(zip(settingnames, zip(tpls, suffixes)))

        self.wf_names = dict()
        self.wf_factories = dict()
        for tpl in set(self.by_settingname.values()):
            obj, suffix = tpl
            prototype = self._prototype(tpl)
            self.wf_names[tpl] = prototype.name
            self.wf_factories[tpl] = deepcopyfactory(prototype)

    def _prototype(self, tpl):
        raise NotImplementedError()

    def _tpl(self, setting):
        raise NotImplementedError()

    def _should_skip(self, obj):
        return obj is None

    def _connect_inputs(self, hierarchy, inputnode, sourcefile, settingname, tpl):
        if hasattr(inputnode.inputs, "repetition_time"):
            self.database.fillmetadata("repetition_time", [sourcefile])
            inputnode.inputs.repetition_time = self.database.metadata(sourcefile, "repetition_time")
        if hasattr(inputnode.inputs, "tags"):
            inputnode.inputs.tags = self.database.tags(sourcefile)
        self.previous_factory.connect(hierarchy, inputnode, sourcefile=sourcefile, settingname=settingname)

    def get(self, sourcefile, settingname):
        hierarchy = self._get_hierarchy("settings_wf", sourcefile=sourcefile)
        wf = hierarchy[-1]

        tpl = self.by_settingname[settingname]

        vwf = wf.get_node(self.wf_names[tpl])
        connect_inputs = False

        if vwf is None:
            connect_inputs = True
            vwf = self.wf_factories[tpl]()
            wf.add_nodes([vwf])

        inputnode = vwf.get_node("inputnode")
        hierarchy.append(vwf)

        if connect_inputs:
            self._connect_inputs(hierarchy, inputnode, sourcefile, settingname, tpl)

        outputnode = vwf.get_node("outputnode")

        return hierarchy, outputnode


class FmriprepAdapterFactory(LookupFactory):
    def _prototype(self, tpl):
        return init_fmriprep_adapter_wf()

    def _tpl(self, setting):
        return None


class SmoothingFactory(LookupFactory):
    def _prototype(self, tpl):
        fwhm, suffix = tpl
        if fwhm is None or float(fwhm) <= 0 or np.isclose(float(fwhm), 0):
            return init_bypass_wf(attrs=["files", "mask", "vals"], name="no_smoothing_wf", suffix=suffix)
        return init_smoothing_wf(fwhm=fwhm, memcalc=self.memcalc, suffix=suffix)

    def _tpl(self, setting):
        smoothing_dict = setting.get("smoothing")

        smoothing = None
        if isinstance(smoothing_dict, dict) and smoothing_dict.get("fwhm") is not None:
            fwhm = smoothing_dict["fwhm"]
            smoothing = f"{fwhm:f}"

        return smoothing


class GrandMeanScalingFactory(LookupFactory):
    def _prototype(self, tpl):
        mean, suffix = tpl
        if mean is None:
            return init_bypass_wf(attrs=["files", "mask", "vals"], name="no_grand_mean_scaling_wf", suffix=suffix)
        return init_grand_mean_scaling_wf(mean=mean, memcalc=self.memcalc, suffix=suffix)

    def _tpl(self, setting):
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

    def _prototype(self, tpl):
        ica_aroma, suffix = tpl
        if ica_aroma is not True:
            return init_bypass_wf(attrs=["files", "mask", "vals"], name="no_ica_aroma_regression_wf", suffix=suffix)
        return init_ica_aroma_regression_wf(workdir=str(self.workdir), memcalc=self.memcalc, suffix=suffix)

    def _tpl(self, setting):
        ica_aroma = setting.get("ica_aroma") is True
        return ica_aroma

    def _connect_inputs(self, hierarchy, inputnode, sourcefile, settingname, tpl):
        super(ICAAROMARegressionFactory, self)._connect_inputs(hierarchy, inputnode, sourcefile, settingname, tpl)
        ica_aroma, suffix = tpl
        if ica_aroma is True:
            self.ica_aroma_components_factory.connect(hierarchy, inputnode, sourcefile=sourcefile, settingname=settingname)


class BandpassFilterFactory(LookupFactory):
    def _prototype(self, tpl):
        bandpass_filter, suffix = tpl
        if bandpass_filter is None:
            return init_bypass_wf(attrs=["files", "mask", "vals"], name="no_bandpass_filter_wf", suffix=suffix)
        return init_bandpass_filter_wf(bandpass_filter=bandpass_filter, memcalc=self.memcalc, suffix=suffix)

    def _tpl(self, setting):
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
    def _prototype(self, tpl):
        _, suffix = tpl
        return init_setting_adapter_wf(suffix=suffix)

    def _tpl(self, setting):
        return None


class ConfoundsSelectFactory(LookupFactory):
    def _prototype(self, tpl):
        confound_names, suffix = tpl
        if confound_names is None:
            return init_bypass_wf(
                attrs=["bold", "confounds", "mask", "vals"],
                unconnected_attrs=["confounds_matrix"],
                name="no_confounds_select_wf",
                suffix=suffix
            )
        return init_confounds_select_wf(confound_names=list(confound_names), suffix=suffix)

    def _tpl(self, setting):
        confounds_removal = setting.get("confounds_removal")

        confound_names = None
        if confounds_removal is not None and len(confounds_removal) > 0:
            confound_names = tuple(sorted(confounds_removal))

        return confound_names


class ConfoundsRegressionFactory(LookupFactory):
    def _prototype(self, tpl):
        has_confounds, suffix = tpl
        if has_confounds is not True:
            return init_bypass_wf(
                attrs=["bold", "confounds_selected", "confounds", "mask", "vals"],
                name="no_confounds_regression_wf",
                suffix=suffix
            )
        return init_confounds_regression_wf(memcalc=self.memcalc, suffix=suffix)

    def _tpl(self, setting):
        confounds_removal = setting.get("confounds_removal")

        has_confounds = False
        if confounds_removal is not None and len(confounds_removal) > 0:
            has_confounds = True

        return has_confounds


class SettingFactory(Factory):
    def __init__(self, ctx, fmriprep_factory):
        super(SettingFactory, self).__init__(ctx)

        self.fmriprep_factory = fmriprep_factory

        self.ica_aroma_components_factory = ICAAROMAComponentsFactory(ctx, self.fmriprep_factory)
        self.fmriprep_adapter_factory = FmriprepAdapterFactory(ctx, self.fmriprep_factory)
        self.smoothing_factory = SmoothingFactory(ctx, self.fmriprep_adapter_factory)
        self.grand_mean_scaling_factory = GrandMeanScalingFactory(ctx, self.smoothing_factory)
        self.ica_aroma_regression_factory = ICAAROMARegressionFactory(ctx, self.grand_mean_scaling_factory, self.ica_aroma_components_factory)
        self.bandpass_filter_factory = BandpassFilterFactory(ctx, self.ica_aroma_regression_factory)

        self.setting_adapter_factory = SettingAdapterFactory(ctx, self.bandpass_filter_factory)
        self.confounds_select_factory = ConfoundsSelectFactory(ctx, self.setting_adapter_factory)
        self.confounds_regression_factory = ConfoundsRegressionFactory(ctx, self.confounds_select_factory)

        settingnames = set(setting["name"] for setting in self.spec.settings if setting.get("output_image") is True)
        self.sourcefiles = self.get_sourcefiles(settingnames)

    def get_sourcefiles(self, settingnames):
        filepaths = set(self.database.get(datatype="func", suffix="bold"))
        ret = set()
        for setting in self.spec.settings:
            if setting.get("name") in settingnames:
                filters = setting.get("filters")
                if filters is None or len(filters) == 0:
                    return filepaths
                else:
                    ret |= self.database.applyfilters(filepaths, filters)
        return ret

    def setup(self, raw_sources_dict=dict()):
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
            setting_output_wf_factory = deepcopyfactory(init_setting_output_wf(workdir=str(self.workdir), settingname=setting["name"]))

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
                tags = {"setting": setting["name"]}
                tags.update(self.database.tags(sourcefile))
                inputnode.inputs.tags = tags
                if raw_sources_dict.get(sourcefile) is not None:
                    inputnode.inputs.metadata = {
                        "raw_sources": raw_sources_dict[sourcefile]
                    }
                self.connect(hierarchy, inputnode, sourcefile, settingname=setting["name"], confounds_action="regression")

    def get(self, sourcefile, settingname, confounds_action=None):
        if confounds_action == "select":
            return self.confounds_select_factory.get(sourcefile, settingname)
        elif confounds_action == "regression":
            return self.confounds_regression_factory.get(sourcefile, settingname)
        elif confounds_action is None:
            return self.setting_adapter_factory.get(sourcefile, settingname)
        else:
            raise ValueError(f"Unknown counfounds action '{confounds_action}'")
