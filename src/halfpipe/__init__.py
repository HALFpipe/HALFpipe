# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from tempfile import mkdtemp

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError

os.environ["NIPYPE_NO_ET"] = "1"  # Disable nipype update check.
os.environ["NIPYPE_NO_MATLAB"] = "1"

os.environ["MPLCONFIGDIR"] = mkdtemp()  # Silence matplotlib warning.

# Special variable set in the container by fMRIPrep.
if os.getenv("IS_DOCKER_8395080871") is not None:
    # We are running in a container, so we reset important
    # env variables to the correct values.

    xdg_cache_home = Path("/var/cache")
    os.environ["XDG_CACHE_HOME"] = str(xdg_cache_home)  # Where matplotlib looks for the font cache.

    halfpipe_resource_dir = xdg_cache_home / "halfpipe"
    os.environ["HALFPIPE_RESOURCE_DIR"] = str(halfpipe_resource_dir)  # Where halfpipe.resource.get looks for its cache.

    templateflow_home = xdg_cache_home / "templateflow"
    os.environ["TEMPLATEFLOW_HOME"] = str(templateflow_home)  # Where templateflow.api looks for its cache.

    del xdg_cache_home, halfpipe_resource_dir, templateflow_home
