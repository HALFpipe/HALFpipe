# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from halfpipe import resource

TESTS_ONLINE_RESOURCES = {
    "wakemandg_hensonrn_statmaps.tar.gz": "https://api.figshare.com/v2/file/download/25621988",
    "ds000108fixed.tar.gz": "https://osf.io/download/qh38c",
    "bids_data.zip": "https://osf.io/download/qrvu4",
    "PNAS_Smith09_rsn10.nii.gz": "https://www.fmrib.ox.ac.uk/datasets/brainmap+rsns/PNAS_Smith09_rsn10.nii.gz",
    "HarvardOxford.tgz": "https://www.nitrc.org/frs/download.php/9902/HarvardOxford.tgz"
}


def setup():
    resource.ONLINE_RESOURCES.update(TESTS_ONLINE_RESOURCES)
