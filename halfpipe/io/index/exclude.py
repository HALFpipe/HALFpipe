# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from functools import lru_cache
import logging

from ...model.exclude import ExcludeSchema, rating_indices
from ...model.tags import entities


def _agg_hierarchy(dicthierarchy, entities=[], **kwargs):
    tagval = None
    if len(entities) > 0:
        entity = entities.pop()
        tagval = kwargs.get(entity)

    if not isinstance(dicthierarchy, dict):
        assert isinstance(dicthierarchy, int)
        return dicthierarchy

    rating = -1
    for k, v in dicthierarchy.items():
        if tagval is not None and k != tagval:
            continue
        if isinstance(v, dict):
            v = _agg_hierarchy(v, entities, **kwargs)
        assert isinstance(v, int)
        if v > rating:
            rating = v

    return rating


def _set_in_hierarchy(dicthierarchy, entities, entry):
    entity = entities.pop()
    tagval = entry.get(entity)

    rating = rating_indices[entry["rating"]]

    if tagval not in dicthierarchy:
        dicthierarchy[tagval] = dict()

    if len(entities) == 0:  # we are at the end of the hierarchy
        if _agg_hierarchy(dicthierarchy[tagval]) > rating:
            return  # ignore lower precedence ratings
        dicthierarchy[tagval] = rating
        return
    else:
        if isinstance(dicthierarchy[tagval], int):
            if dicthierarchy[tagval] > rating:
                return  # ignore lower precedence ratings
            dicthierarchy[tagval] = dict()  # overwrite parent with higher precedence child values
        _set_in_hierarchy(dicthierarchy[tagval], entities, entry)  # go down hierarchy
        return

    raise ValueError(f'Unexpected value "{dicthierarchy[tagval]}"')


class ExcludeDatabase:
    def __init__(self, excludefiles):
        exclude_schema = ExcludeSchema(many=True)

        dicthierarchy = dict()

        for excludefile in excludefiles:
            with open(excludefile, "r") as fp:
                entries = exclude_schema.loads(fp.read())

            for entry in entries:
                for i, entity in enumerate(entities):  # order determines entity precedence
                    if entity in entry:
                        break
                _set_in_hierarchy(dicthierarchy, [*entities[i:]], entry)

        self.dicthierarchy = dicthierarchy

    def get(self, **kwargs):
        rating = _agg_hierarchy(self.dicthierarchy, entities=[*entities], **kwargs)

        if rating == 2:  # rating "bad"
            return True  # yes, exclude this

        if rating == 0:  # rating "good"
            return False  # no, don't exclude

        rating_str = None
        for r_str, r in rating_indices.items():
            if r == rating:
                rating_str = r_str
        assert rating_str is not None, f'Unknown rating int value "{rating}"'

        query_str = " ".join([f'{k}="{v}"' for k, v in kwargs.items()])

        logging.getLogger("halfpipe").warning(
            f'Will include observation ({query_str}) for analysis '
            f'even though quality rating is "{rating_str}"'
        )

        return False  # no, don't exclude

    @classmethod
    @lru_cache(maxsize=128)
    def cached(cls, excludefile):
        return cls(excludefile)
