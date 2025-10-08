# -*- coding: utf-8 -*-


import os
import re
import shutil
from datetime import datetime
from typing import Any, Callable, List, Optional, Set

from textual.css.query import NoMatches  # Import the NoMatches exception

from ..collect.events import collect_events
from ..ingest.events import ConditionFile
from ..logging import logger
from ..model.filter import FilterSchema
from .data_analyzers.context import ctx


def extract_name_part(template_path: str, file_path: str, tag: str = "desc") -> Optional[str]:
    """
    Extracts a specific part from a file path based on a template.

    This function uses regular expressions to extract a dynamic part from a
    file path, given a template that includes a placeholder. The placeholder
    is defined by the `suffix` parameter.

    Parameters
    ----------
    template_path : str
        The template string that includes a placeholder for dynamic matching.
        Example: "/path/to/data/{atlas}/file.nii.gz".
    file_path : str
        The actual file path from which a part will be extracted based on the
        template. Example: "/path/to/data/my_atlas/file.nii.gz".
    file_tag : str, optional
        The suffix used to create the placeholder in the `template_path`
        (default is "atlas").

    Returns
    -------
    Optional[str]
        The extracted part of the file path if a match is found, otherwise
        None. In the example above, if `file_tag` is "atlas", it would return
        "my_atlas".
    """
    # Create a regex pattern dynamically based on the template
    placeholder = f"{{{tag}}}"
    pattern = re.escape(template_path).replace(re.escape(placeholder), rf"(?P<{tag}>.+)")
    #
    # Search for the atlas part using the regex pattern
    match = re.search(pattern, file_path)
    #
    if match:
        return match.group(tag)
    else:
        return None  # Return None if no match is found


def extract_conditions(entity: str, values: List[str]) -> List[str]:
    """
    Extracts conditions based on a given entity and its values.

    This function filters the available data based on the provided entity
    and values, and then extracts the unique conditions associated with the
    filtered data.

    Parameters
    ----------
    entity : str
        The entity for which conditions are being extracted.
        Example: "task", "run".
    values : List[str]
        The values associated with the entity.
        Example: ["rest", "nback"].

    Returns
    -------
    List[str]
        The conditions obtained after applying the filter.
        Example: ["condition_a", "condition_b"].
    """
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


def get_conditions(_filter: Any) -> List[str]:
    """
    Retrieves unique conditions from event files associated with BOLD files.

    This function finds BOLD file paths based on the provided filter, then
    collects event files associated with those BOLD files. It extracts and
    returns a list of unique conditions found in those event files.

    Parameters
    ----------
    _filter : Any
        The filter criteria used to find bold file paths. This can be a
        callable filter function or None.

    Returns
    -------
    List[str]
        A list of unique conditions extracted from event file paths
        associated with the bold file paths.
        Example: ["condition_a", "condition_b"].
    """
    bold_file_paths = find_bold_file_paths(_filter)

    conditions: list[str] = list()
    seen = set()
    for bold_file_path in bold_file_paths:
        event_file_paths = collect_events(ctx.database, bold_file_path)
        logger.debug(f"IU->get_conditions-> event_file_paths:{event_file_paths}, bold_file_path:{bold_file_path}")
        if event_file_paths is None:
            continue

        if event_file_paths in seen:
            continue

        cf = ConditionFile(data=event_file_paths)
        for condition in cf.conditions:  # maintain order
            if condition not in conditions:
                conditions.append(condition)
        logger.debug(f"IU->get_conditions-> conditions:{conditions}")

        seen.add(event_file_paths)
    return conditions


def find_bold_file_paths(_filter: Optional[Callable] = None) -> Set[str]:
    """
    Finds BOLD file paths in the database, optionally applying a filter.

    This function retrieves BOLD file paths from the context database and
    optionally applies a filter to the retrieved paths.

    Parameters
    ----------
    _filter : Optional[Callable], optional
        A filter function to apply to the set of BOLD file paths retrieved
        from the database. If None, no filtering is applied.
        The filter function should take a set of file paths as input and
        return a filtered set of file paths.

    Returns
    -------
    Set[str]
        A set of BOLD file paths after applying the optional filter.

    Raises
    ------
    ValueError
        If no BOLD files are found in the database.
    """
    bold_file_paths = ctx.database.get(datatype="func", suffix="bold")

    if bold_file_paths is None:
        raise ValueError("No BOLD files in database")

    bold_file_paths = set(bold_file_paths)

    if _filter is not None:
        bold_file_paths = ctx.database.applyfilters(bold_file_paths, [_filter])

    return bold_file_paths


def tag_the_string(tagvals: List[str]) -> List[str]:
    """
    Wraps each string in a list with double quotes.

    This function takes a list of strings and returns a new list where each
    string is wrapped in double quotes.

    Parameters
    ----------
    tagvals : List[str]
        A list of string elements that need to be wrapped in double quotes.

    Returns
    -------
    List[str]
        A new list with each original string element wrapped in double quotes.
        Example: ['"value1"', '"value2"'].
    """
    return [f'"{tagval}"' for tagval in tagvals]


def copy_and_rename_file(src_file: str) -> str:
    """
    Copies a file and renames the copy with a timestamp.

    This function copies a file to the same directory, appending a timestamp
    to the filename to create a unique backup.

    Parameters
    ----------
    src_file : str
        The path to the source file that needs to be copied and renamed.

    Returns
    -------
    str
        The path to the newly created copy of the file with the timestamped
        filename.
    """
    # Get the directory, filename, and extension
    dir_name, file_name = os.path.split(src_file)
    file_base, file_ext = os.path.splitext(file_name)

    # Create a timestamp in YYYY-MM-DD_HH-MM format
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

    # Create the new filename
    new_file_name = f"{file_base}_{timestamp}{file_ext}"
    new_file_path = os.path.join(dir_name, new_file_name)

    # Copy the file and rename it
    shutil.copy(src_file, new_file_path)

    return new_file_path


def widget_exists(where: Any, widget: str) -> bool:
    """
    Checks if a widget with a specific ID exists within a container.

    This function attempts to find a widget with the given ID within the
    specified container. It returns True if the widget exists, and False
    otherwise.

    Parameters
    ----------
    where : Any
        The container (e.g., a widget or an app) in which to search for the
        widget.
    widget : str
        The ID of the widget to search for.

    Returns
    -------
    bool
        True if the widget exists, False otherwise.
    """
    try:
        where.get_widget_by_id(widget)
        return True
    except NoMatches:
        return False


def is_number_string(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
