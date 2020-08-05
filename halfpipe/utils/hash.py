# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


def hexdigest(obj):
    import hashlib
    import json

    m = hashlib.sha1()
    m.update(json.dumps(obj, sort_keys=True).encode())
    return m.hexdigest()
