# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from .json import TypeAwareJSONEncoder


def int_digest(obj) -> int:
    return int(hex_digest(obj), 16)


def hex_digest(obj):
    import json
    from hashlib import sha1

    m = sha1()
    m.update(json.dumps(obj, sort_keys=True, cls=TypeAwareJSONEncoder).encode())
    return m.hexdigest()


def b32_digest(obj):
    import json
    from base64 import b32encode
    from hashlib import sha1

    m = sha1()
    m.update(json.dumps(obj, sort_keys=True, cls=TypeAwareJSONEncoder).encode())
    return b32encode(m.digest()).decode("utf-8").replace("=", "").lower()
