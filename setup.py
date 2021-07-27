#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
""" setup script """

import sys
from setuptools import setup
import versioneer
import re

git_requirement_re = re.compile(r"git\+.+/(?P<package_name>[a-z]).git")


# Give setuptools a hint to complain if it's too old a version
# 40.8.0 allows us to put most metadata in setup.cfg
# Should match pyproject.toml
setup_requires = ["setuptools >= 40.8"]
# This enables setuptools to install wheel on-the-fly
setup_requires += ["wheel"] if "bdist_wheel" in sys.argv else []

with open("requirements.in", "rt") as requirements_file_handle:
    install_requires = list()
    for requirement in requirements_file_handle.readlines():
        requirement = requirement.strip()

        if "#" in requirement:
            continue

        if not requirement.startswith("git+"):
            install_requires.append(requirement)
            continue

        match = git_requirement_re.search(requirement)
        assert match is not None
        install_requires.append(match.group("package_name"))

if __name__ == "__main__":
    setup(
        name="halfpipe",
        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),
        setup_requires=setup_requires,
        install_requires=install_requires,
    )
