# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from halfpipe import resource

TESTS_ONLINE_RESOURCES = {
    "wakemandg_hensonrn_statmaps.tar.gz": "https://api.figshare.com/v2/file/download/25621988",
}


def setup():
    resource.ONLINE_RESOURCES.update(TESTS_ONLINE_RESOURCES)
