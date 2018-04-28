#!/usr/bin/env python
# -*- coding: utf-8 -*-

def main():
    """ Install entry-point """
    from io import open
    from os import path as op
    from inspect import getfile, currentframe
    from setuptools import setup, find_packages
    from setuptools.extension import Extension
    from numpy import get_include

    this_path = op.dirname(op.abspath(getfile(currentframe())))

    # Python 3: use a locals dictionary
    # http://stackoverflow.com/a/1463370/6820620
    ldict = locals()
    # Get version and release info, which is all stored in pipeline/info.py
    module_file = op.join(this_path, 'pipeline', 'info.py')
    with open(module_file) as infofile:
        pythoncode = [line for line in infofile.readlines() if not line.strip().startswith('#')]
        exec('\n'.join(pythoncode), globals(), ldict)

    extensions = []

    setup(
        name=ldict['__packagename__'],
        version=ldict['__version__'],
        description=ldict['__description__'],
        long_description=ldict['__longdesc__'],
        author=ldict['__author__'],
        author_email=ldict['__email__'],
        maintainer=ldict['__maintainer__'],
        maintainer_email=ldict['__email__'],
        url=ldict['__url__'],
        license=ldict['__license__'],
        classifiers=ldict['CLASSIFIERS'],
        download_url=ldict['DOWNLOAD_URL'],
        # Dependencies handling
        setup_requires=ldict['SETUP_REQUIRES'],
        install_requires=ldict['REQUIRES'],
        tests_require=ldict['TESTS_REQUIRES'],
        extras_require=ldict['EXTRA_REQUIRES'],
        dependency_links=ldict['LINKS_REQUIRES'],
        package_data={},
        entry_points={'console_scripts': [
            'pipeline=pipeline.run:main'
        ]},
        packages=find_packages(exclude=("tests",)),
        zip_safe=False,
        ext_modules=extensions
    )

if __name__ == '__main__':
    main()
