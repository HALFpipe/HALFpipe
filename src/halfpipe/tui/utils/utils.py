# -*- coding: utf-8 -*-


import re

from ...collect.events import collect_events
from ...ingest.events import ConditionFile
from ...model.filter import FilterSchema
from .context import ctx


def extract_name_part(template_path, file_path, suffix="atlas"):
    # Create a regex pattern dynamically based on the template
    placeholder = f"{{{suffix}}}"
    pattern = re.escape(template_path).replace(re.escape(placeholder), rf"(?P<{suffix}>.+)")
    #
    # Search for the atlas part using the regex pattern
    match = re.search(pattern, file_path)
    #
    if match:
        return match.group(suffix)
    else:
        return None  # Return None if no match is found


def extract_conditions(entity, values):
    filter_schema = FilterSchema()
    _filter = filter_schema.load(
        {
            "type": "tag",
            "action": "include",
            "entity": entity,
            "values": values,
        }
    )
    return get_conditions(_filter)


def get_conditions(_filter):
    bold_file_paths = find_bold_file_paths(_filter)

    conditions: list[str] = list()
    seen = set()
    for bold_file_path in bold_file_paths:
        event_file_paths = collect_events(ctx.database, bold_file_path)
        print("event_file_pathsevent_file_pathsevent_file_paths", event_file_paths)
        if event_file_paths is None:
            continue

        if event_file_paths in seen:
            continue

        cf = ConditionFile(data=event_file_paths)
        for condition in cf.conditions:  # maintain order
            if condition not in conditions:
                conditions.append(condition)

        seen.add(event_file_paths)
    print("conditionsconditionsconditionsconditions", conditions)
    return conditions


def find_bold_file_paths(_filter):
    bold_file_paths = ctx.database.get(datatype="func", suffix="bold")

    if bold_file_paths is None:
        raise ValueError("No BOLD files in database")

    #  filters = ctx.spec.settings[-1].get("filters")
    bold_file_paths = set(bold_file_paths)

    if _filter is not None:
        bold_file_paths = ctx.database.applyfilters(bold_file_paths, [_filter])

    return bold_file_paths


def tag_the_string(tagvals):
    return [f'"{tagval}"' for tagval in tagvals]
