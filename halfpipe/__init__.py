# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from pathlib import Path
from tempfile import mkdtemp

from ._version import get_versions
__version__ = get_versions()["version"]
del get_versions

os.environ["NIPYPE_NO_ET"] = "1"  # disable nipype update check
os.environ["NIPYPE_NO_MATLAB"] = "1"

halfpipe_resource_dir = Path("/home/fmriprep/.cache/halfpipe")
if halfpipe_resource_dir.is_dir():
    os.environ["HALFPIPE_RESOURCE_DIR"] = str(halfpipe_resource_dir)
templateflow_home = Path("/home/fmriprep/.cache/templateflow")
if templateflow_home.is_dir():
    os.environ["TEMPLATEFLOW_HOME"] = str(templateflow_home)
del halfpipe_resource_dir, templateflow_home

os.environ["MPLCONFIGDIR"] = mkdtemp()  # silence matplotlib warning
