# -*- coding: utf-8 -*-

from typing import ClassVar, Dict, List, Type, Union

from ...model.file.anat import T1wFileSchema
from ...model.file.base import BaseFileSchema
from ...model.file.fmap import (
    BaseFmapFileSchema,
)
from ...model.file.func import (
    BoldFileSchema,
)
from ...model.file.schema import FileSchema
from ...model.tags import entity_longnames as entity_display_aliases
from ...model.utils import get_schema_entities
from ...utils.format import inflect_engine as p
from ..data_analyzers.context import ctx


def messagefun(
    database, filetype, filepaths, tagnames, entity_display_aliases: dict | None = None
) -> tuple[str, dict[str, int]]:
    """
    Generates a summary message about files and their tag distributions.

    This function creates a human-readable message summarizing the number of
    files found and the distribution of tag values across those files.

    Parameters
    ----------
    database : Database
        An instance of the database connection used to retrieve tag values.
    filetype : str
        The type of files that are being queried (e.g., "T1-weighted image").
    filepaths : list[str]
        A list of file paths that are being processed.
    tagnames : list[str]
        A list of tags to be checked in the filepaths (e.g., ["task", "acq"]).
    entity_display_aliases : dict[str, str], optional
        An optional dictionary for aliasing tag names for display.
        For example, {"acq": "acquisition"}, by default None.

    Returns
    -------
    tuple[str, dict[str, int]]
        A tuple containing:
        - A message string summarizing the files and their tag distributions.
        - A dictionary where keys are tag names and values are the number of
          unique values for that tag across the files.
    """

    entity_display_aliases = dict() if entity_display_aliases is None else entity_display_aliases
    message = ""
    n_by_tag = {}
    if filepaths is not None:
        message = p.inflect(f"Found {len(filepaths)} {filetype} plural('file', {len(filepaths)})")
        if len(filepaths) > 0:
            for tagname in tagnames:
                tagvalset = database.tagvalset(tagname, filepaths=filepaths)
                if tagvalset is not None:
                    n_by_tag[tagname] = len(tagvalset)
            tagmessages = [
                p.inflect(f"{n} plural('{entity_display_aliases.get(tagname, tagname)}', {n})")
                for tagname, n in n_by_tag.items()
                if n > 0
            ]
            message += " "
            message += "for"
            message += " "
            message += p.join(tagmessages)
    return message, n_by_tag


class FilePatternSummaryStep:
    """
    Base class for generating summaries of file patterns.

    This class provides a framework for generating summaries for specific
    file patterns. It retrieves file paths from a database, generates a
    message regarding those files, and summarizes the information.

    Attributes
    ----------
    entity_display_aliases : ClassVar[Dict[str, str]]
        A dictionary containing aliases for displaying various entities.
    filetype_str : ClassVar[str]
        A string representing the type of file.
    filedict : Dict[str, str]
        A dictionary that is used to retrieve file paths from the database.
    schema : Union[Type[BaseFileSchema], Type[FileSchema]]
        A schema to extract schema entities.
    entities : list[str]
        List of entities extracted from the schema.
    filepaths : list[str]
        List of filepaths retrieved from the database.
    message : str
        The generated summary message.
    n_by_tag : dict[str, int]
        A dictionary where keys are tag names and values are the number of
        unique values for that tag across the files.

    Methods
    -------
    get_message : property
        Returns the generated message.
    get_summary : property
        Returns a summary dictionary containing the generated message,
        the file paths, and the tag distribution.
    """

    entity_display_aliases: ClassVar[Dict] = entity_display_aliases

    filetype_str: ClassVar[str] = "file"
    filedict: Dict[str, str] = dict()
    schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema

    def __init__(self):
        """
        Initializes the FilePatternSummaryStep.

        This method extracts schema entities, retrieves file paths from the
        database, and generates a summary message.
        """
        self.entities = get_schema_entities(self.schema)  # Assumes a function to extract schema entities

        # Assuming ctx and database are accessible here
        self.filepaths = ctx.database.get(**self.filedict)
        self.message, self.n_by_tag = messagefun(
            ctx.database,
            self.filetype_str,
            self.filepaths,
            self.entities,
            entity_display_aliases,  # This should be defined somewhere accessible
        )

    @property
    def get_message(self) -> str:
        """
        Returns the generated summary message.

        Returns
        -------
        str
            The summary message.
        """
        return self.message

    @property
    def get_summary(self) -> Dict[str, Union[str, List[str], Dict[str, int]]]:
        """
        Returns a summary dictionary.

        Returns
        -------
        Dict[str, Union[str, List[str], Dict[str, int]]]
            A dictionary containing the summary message, the file paths,
            and the tag distribution.
        """
        return {"message": self.message, "files": self.filepaths, "n_by_tag": self.n_by_tag}


class AnatSummaryStep(FilePatternSummaryStep):
    """
    Summary step for anatomical (T1-weighted) imaging files.

    This class extends FilePatternSummaryStep to provide a summary
    specifically for T1-weighted anatomical images.

    Attributes
    ----------
    filetype_str : str
        Descriptive string for the type of file, indicating it is a
        "T1-weighted image".
    filedict : dict[str, str]
        Dictionary defining the file pattern components, here specifying
        that the `datatype` is "anat" and the `suffix` is "T1w".
    schema : Type[T1wFileSchema]
        Schema class used for validating and processing T1-weighted
        image files.
    """

    filetype_str = "T1-weighted image"
    filedict = {"datatype": "anat", "suffix": "T1w"}
    schema = T1wFileSchema


class BoldSummaryStep(FilePatternSummaryStep):
    """
    Summary step for functional BOLD files.

    This class extends FilePatternSummaryStep to provide a summary
    specifically for BOLD images.

    Attributes
    ----------
    filetype_str : str
        Descriptive string for the type of file, indicating it is a
        BOLD image.
    filedict : dict[str, str]
        Dictionary defining the file pattern components, here specifying
        that the `datatype` is "func" and the `suffix` is "bold".
    schema : Type[BoldFileSchema]
        Schema class used for validating and processing BOLD image files.
    """

    filetype_str = "BOLD image"
    filedict = {"datatype": "func", "suffix": "bold"}
    schema = BoldFileSchema


class FmapSummaryStep(FilePatternSummaryStep):
    """
    Summary step for field map images.

    This class extends FilePatternSummaryStep to provide a summary
    specifically for field map images.

    Attributes
    ----------
    filetype_str : str
        Descriptive string for the type of file, indicating it is a
        field map image.
    filedict : dict[str, str]
        Dictionary defining the file pattern components, here specifying
        that the `datatype` is "fmap".
    schema : Type[BaseFmapFileSchema]
        A schema class that defines the structure and constraints of
        the field map files.
    """

    filetype_str = "field map image"
    filedict = {"datatype": "fmap"}
    schema = BaseFmapFileSchema
