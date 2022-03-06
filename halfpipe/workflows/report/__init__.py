# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from .anat import init_anat_report_wf
from .func import init_func_report_wf

__all__ = ["init_anat_report_wf", "init_func_report_wf"]
