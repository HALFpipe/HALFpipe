# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional

from os import getenv
from pathlib import Path
from templateflow import api

DEFAULT_HALFPIPE_RESOURCE_DIR = Path.home() / ".cache" / "halfpipe"
HALFPIPE_RESOURCE_DIR = Path(getenv("HALFPIPE_RESOURCE_DIR", str(DEFAULT_HALFPIPE_RESOURCE_DIR)))

ONLINE_RESOURCES = {
    "index.html": "https://github.com/mindandbrain/qualitycheck/releases/download/0.2.2/index.html",
    "tpl_MNI152NLin6Asym_from_MNI152NLin2009cAsym_mode_image_xfm.h5": "https://api.figshare.com/v2/file/download/5534327",
    "tpl_MNI152NLin2009cAsym_from_MNI152NLin6Asym_mode_image_xfm.h5": "https://api.figshare.com/v2/file/download/5534330",
    "tpl-MNI152NLin2009cAsym_RegistrationCheckOverlay.nii.gz": "https://api.figshare.com/v2/file/download/22447958",
}

MNI152NLin2009cAsym_xfmpaths = api.get("MNI152NLin2009cAsym", suffix="xfm")
TF_RESOURCES = dict()


if not HALFPIPE_RESOURCE_DIR.exists() or not list(HALFPIPE_RESOURCE_DIR.iterdir()):
    HALFPIPE_RESOURCE_DIR.mkdir(exist_ok=True, parents=True)


def download(url: str, target=None) -> Optional[str]:
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
        res = fp.getvalue().decode()

    t.close()
    fp.close()

    return res


def get(filename=None) -> str:
    if filename in TF_RESOURCES:
        return TF_RESOURCES[filename]

    assert filename in ONLINE_RESOURCES, f"Resource {filename} not found"

    filepath = HALFPIPE_RESOURCE_DIR / filename
    if filepath.exists():
        return filepath

    resource = ONLINE_RESOURCES[filename]

    if isinstance(resource, tuple):
        import json

        jsonstr = download(resource[0])
        assert isinstance(jsonstr, str)

        accval = json.loads(jsonstr)
        for key in resource[1:]:
            accval = accval[key]
        resource = accval

    download(resource, target=filepath)

    return str(filepath)
