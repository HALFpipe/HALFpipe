# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def hex_digest(obj):
    from hashlib import sha1
    import json

    m = sha1()
    m.update(json.dumps(obj, sort_keys=True).encode())
    return m.hexdigest()


def b32_digest(obj):
    from hashlib import sha1
    import json
    from base64 import b32encode

    m = sha1()
    m.update(json.dumps(obj, sort_keys=True).encode())
    return b32encode(m.digest()).decode("utf-8").replace("=", "").lower()
