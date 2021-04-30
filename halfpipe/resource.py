# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional

from os import getenv
from pathlib import Path
from templateflow import api
import templateflow

default_resource_dir = Path.home() / ".cache" / "halfpipe"
resource_dir = Path(
    getenv("HALFPIPE_RESOURCE_DIR", str(default_resource_dir))
)
resource_dir.mkdir(exist_ok=True, parents=True)

online_resources = dict([
    (
        "index.html",
        "https://github.com/HALFpipe/QualityCheck/releases/download/0.3.0/index.html",
    ),
    (
        "tpl_MNI152NLin6Asym_from_MNI152NLin2009cAsym_mode_image_xfm.h5",
        "https://api.figshare.com/v2/file/download/5534327",
    ),
    (
        "tpl_MNI152NLin2009cAsym_from_MNI152NLin6Asym_mode_image_xfm.h5",
        "https://api.figshare.com/v2/file/download/5534330",
    ),
    (
        "tpl-MNI152NLin2009cAsym_RegistrationCheckOverlay.nii.gz",
        "https://api.figshare.com/v2/file/download/22447958",
    ),
])

xfmpaths = api.get("MNI152NLin2009cAsym", suffix="xfm")
templateflow_resources = dict()


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
    if filename in templateflow_resources:
        return templateflow_resources[filename]

    assert filename in online_resources, f"Resource {filename} not found"

    filepath = resource_dir / filename
    if filepath.exists():
        return filepath

    resource = online_resources[filename]

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


if __name__ == "__main__":
    spaces = ["MNI152NLin6Asym", "MNI152NLin2009cAsym"]
    for space in spaces:
        paths = api.get(space, atlas=None)
        assert isinstance(paths, list)
        assert len(paths) > 0
    for filename in online_resources.keys():
        get(filename=filename)
