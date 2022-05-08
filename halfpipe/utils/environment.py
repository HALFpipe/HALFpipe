# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import os
from argparse import Namespace
from glob import glob
from pathlib import Path

from .path import resolve

logger = logging.getLogger()


def setup_freesurfer_env(opts: Namespace) -> bool:
    """Configure the FS_LICENSE env var

    Args:
      opts: an argparser.Namespace with provided halfpipe arguments

    Returns:
      Boolean value representing the state of the freesurfer license config
    """
    if os.environ.get("FS_LICENSE") is not None:
        logger.debug(f'Using FreeSurfer license "{os.environ["FS_LICENSE"]}"')
        return True

    if opts.fs_license_file is not None:
        fs_license_file = resolve(opts.fs_license_file, opts.fs_root)
        if fs_license_file.is_file():
            os.environ["FS_LICENSE"] = str(fs_license_file)
            return True
    else:
        license_files = list(glob(str(Path(opts.workdir) / "*license*")))

        if len(license_files) > 0:
            license_file = str(license_files[0])
            os.environ["FS_LICENSE"] = license_file
            return True

    return False
