# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Any, Sequence

from ..logging import logger
from ..utils.ops import check_almost_equal


def dictionary_contains(target: dict, query: dict) -> bool:
    for key, query_value in query.items():
        value = target.get(key)
        if query_value is None:
            if value is None:
                logger.debug(f'Matched null for key "{key}"')
                continue
            if isinstance(value, Sequence) and len(value) == 0:
                logger.debug(f'Matched empty sequency for key "{key}"')
                continue
        elif key not in target:
            pass
        if isinstance(value, dict) and isinstance(query_value, dict):
            if dictionary_contains(value, query_value):
                logger.debug(f'Matched dictionary for key "{key}"')
                continue
        elif check_almost_equal(value, query_value):
            logger.debug(f'Matched value for key "{key}"')
            continue
        logger.debug(f"Failed on dict {key} with {value} and {query_value}")
        return False
    return True


def map_setting_to_template(target: dict[str, Any], setting_templates: dict[str, dict[str, Any]]) -> str | None:
    for template_name, setting_template in setting_templates.items():
        logger.debug(f"Checking {template_name}")
        if dictionary_contains(target, setting_template):
            logger.debug(f"Matched {template_name}")
            return template_name
    return None
