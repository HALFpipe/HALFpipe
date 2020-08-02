# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .fixes import ApplyTransforms, FLAMEO, MultipleRegressDesign
from .fslnumpy import FilterRegressor, TemporalFilter
from .imagemaths import AddMeans, Merge, MergeMask, Resample
from .preprocessing import GrandMeanScaling
from .report import PlotEpi, PlotRegistration, Vals
from .resultdict import (
    MakeResultdicts,
    FilterResultdicts,
    AggregateResultdicts,
    ExtractFromResultdict,
    ResultdictDatasink,
)
from .stats import MakeDofVolume, InterceptOnlyModel, LinearModel
from .utility import (
    Exec,
    Filter,
    Interleave,
    Select,
    ToAFNI,
    FromAFNI,
    LoadResult,
    MergeColumns,
    SelectColumns,
)

__all__ = [
    ApplyTransforms,
    FLAMEO,
    MultipleRegressDesign,
    FilterRegressor,
    TemporalFilter,
    AddMeans,
    Merge,
    MergeMask,
    Resample,
    GrandMeanScaling,
    PlotEpi,
    PlotRegistration,
    Vals,
    MakeResultdicts,
    FilterResultdicts,
    AggregateResultdicts,
    ExtractFromResultdict,
    ResultdictDatasink,
    MakeDofVolume,
    InterceptOnlyModel,
    LinearModel,
    Exec,
    Filter,
    Interleave,
    Select,
    ToAFNI,
    FromAFNI,
    LoadResult,
    MergeColumns,
    SelectColumns,
]
