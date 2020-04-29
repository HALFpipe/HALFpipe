# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import getenv
from pathlib import Path
from templateflow import api

DEFAULT_PIPELINE_RESOURCE_DIR = Path.home() / ".cache" / "pipeline"
PIPELINE_RESOURCE_DIR = Path(
    getenv("PIPELINE_RESOURCE_DIR", str(DEFAULT_PIPELINE_RESOURCE_DIR))
)

ONLINE_RESOURCES = {
    "index.html": (
        "https://api.github.com/repos/mindandbrain/qualitycheck/releases/latest",
        "assets",
        0,
        "browser_download_url",
    ),
    "tpl_MNI152NLin6Asym_from_MNI152NLin2009cAsym_mode_image_xfm.h5": "https://api.figshare.com/v2/file/download/5534327",
    "tpl_MNI152NLin2009cAsym_from_MNI152NLin6Asym_mode_image_xfm.h5": "https://api.figshare.com/v2/file/download/5534330",
    "tpl-MNI152NLin2009cAsym_RegistrationCheckOverlay.nii.gz": "https://api.figshare.com/v2/file/download/22447958",
}

MNI152NLin2009cAsym_xfmpaths = api.get("MNI152NLin2009cAsym", suffix="xfm")
# MNI152NLin2009cAsym_from_MNI152NLin6Asym_xfmpath = next(
#     xfmpath for xfmpath in MNI152NLin2009cAsym_xfmpaths if "MNI152NLin6Asym" in str(xfmpath)
# )
TF_RESOURCES = {
    # "tpl_MNI152NLin2009cAsym_from_MNI152NLin6Asym_mode_image_xfm.h5": MNI152NLin2009cAsym_from_MNI152NLin6Asym_xfmpath
}


if not PIPELINE_RESOURCE_DIR.exists() or not list(PIPELINE_RESOURCE_DIR.iterdir()):
    PIPELINE_RESOURCE_DIR.mkdir(exist_ok=True, parents=True)


def download(url, target=None):
    import requests
    from tqdm import tqdm
    import io

    if target is not None:
        fp = open(target, "wb")
    else:
        fp = io.BytesIO()

    print(f"Downloading {url}")

    with requests.get(url, stream=True) as rq:
        total_size = int(rq.headers.get("content-length", 0))
        block_size = 1024

        t = tqdm(total=total_size, unit="B", unit_scale=True)

        for block in rq.iter_content(block_size):
            if block:  # filter out keep-alive new chunks
                t.update(len(block))
                fp.write(block)

    res = None
    if isinstance(fp, io.BytesIO):
        res = fp.getvalue()

    t.close()
    fp.close()

    return res


def get(filename=None):
    if filename in TF_RESOURCES:
        return TF_RESOURCES[filename]

    if filename in ONLINE_RESOURCES:
        filepath = PIPELINE_RESOURCE_DIR / filename
        if filepath.exists():
            return filepath

        resource = ONLINE_RESOURCES[filename]

        if isinstance(resource, tuple):
            import json

            accval = json.loads(download(resource[0]))
            for key in resource[1:]:
                accval = accval[key]
            resource = accval

        download(resource, target=filepath)

        return filepath
