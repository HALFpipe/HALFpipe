# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import marshmallow
from marshmallow import EXCLUDE
import json
from pathlib import Path
from inflection import underscore

from ...model.metadata import MetadataSchema
from ...utils import splitext


class SidecarMetadataLoader:
    cache = dict()

    @classmethod
    def loadjson(cls, fname):
        stem, _ = splitext(fname)
        sidecarfile = Path(fname).parent / f"{stem}.json"

        if not Path(sidecarfile).is_file():
            return

        with open(sidecarfile, "r") as fp:
            jsn = fp.read()

        return json.loads(jsn)

    @classmethod
    def load(cls, fname):
        if fname in cls.cache:
            return cls.cache[fname]

        try:
            in_data = cls.loadjson(fname)

            if in_data is None:
                return

            # data transformations
            try:
                from sdcflows.interfaces.fmap import get_ees
                # get effective echo spacing even if not explicitly specified
                in_data["EffectiveEchoSpacing"] = get_ees(in_data, in_file=fname)
            except Exception:
                pass

            if "EchoTime1" in in_data and "EchoTime2" in in_data:
                if "EchoTimeDifference" not in in_data:
                    in_data["EchoTimeDifference"] = abs(
                        float(in_data["EchoTime1"]) - float(in_data["EchoTime2"])
                    )

            # parse
            in_data = {underscore(k): v for k, v in in_data.items()}
            sidecar = MetadataSchema().load(in_data, unknown=EXCLUDE)
        except marshmallow.exceptions.ValidationError:
            return

        cls.cache[fname] = sidecar
        return sidecar

    def fill(self, fileobj, key):
        sidecar = self.load(fileobj.path)

        if sidecar is None:
            return False

        value = sidecar.get(key)

        if value is None:
            return False

        fileobj.metadata[key] = value
        return True
