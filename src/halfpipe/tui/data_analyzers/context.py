# -*- coding: utf-8 -*-
from collections import defaultdict
from pathlib import Path
from typing import Any

from inflection import humanize

from ...ingest.database import Database
from ...logging import logger
from ...model.spec import Spec, SpecSchema
from ...model.tags import entities
from ..standards import entity_colors, entity_display_aliases


# This is a singleton!
class Context:
    """
    Context class for managing global application state and data.

    This class is implemented as a singleton to ensure that there is only one
    instance of the context throughout the application. It provides access to
    the spec file, the database, the working directory, and a cache
    for storing various user choices. The cache is a nested dictionary with the
    following structure: Widget ID -> type of data, e.g., features, settings,
    models and then within these subdictionaries we have the particular user
    choices.

    Attributes
    ----------
    spec : Spec
        The specification object containing the configuration for the application.
    database : Database
        The database object for managing data storage and retrieval.
    workdir : Path | None
        The working directory for the application, where output files are stored.
    use_existing_spec : bool
        Flag indicating whether to use an existing specification file.
    debug : bool
        Flag indicating whether the application is in debug mode.
    already_checked : set[str]
        Set of strings representing items that have already been checked. For more
        see meta_data_steps.py.
    cache : defaultdict[str, defaultdict[str, dict[str, Any]]]
        A nested defaultdict used as a cache for storing various data.
        The structure is: cache[top_level_key][second_level_key] = {data_key: data_value}
    available_images : dict
        A dictionary storing available images, keyed by entity type (e.g., 'task').
        The values are lists of available tags for each entity.

    """

    _instance = None
    _initialized: bool

    def __new__(cls, *args, **kwargs):
        """
        Ensures that only one instance of the Context class is created.

        This method implements the singleton pattern by checking if an instance
        already exists. If it does, it returns the existing instance; otherwise,
        it creates a new one.

        Returns
        -------
        Context
            The singleton instance of the Context class.

        """
        if cls._instance is None:
            cls._instance = super(Context, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """
        Initializes the Context object.

        This method sets up the default values for the specification, database,
        working directory, and other attributes. It also initializes the cache
        and sets the _initialized flag to True.

        """
        if self._initialized:
            return
        spec_schema = SpecSchema()
        spec = spec_schema.load(spec_schema.dump({}), partial=True)
        assert isinstance(spec, Spec)
        self.spec: Spec = spec  # initialize with defaults
        self.database = Database(self.spec)
        self.workdir: Path | None = None
        self.fs_license_file: Path | None = None
        self.use_existing_spec = False
        self.debug = False
        self.already_checked: set[str] = set()
        self._initialized = True
        self.cache: defaultdict[str, defaultdict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
        self.available_images: dict = {}

    def put(self, fileobj):
        """Adds a file object to the database.

        Parameters
        ----------
        fileobj : Any
            The file object to be added to the database.

        Returns
        -------
        int
            The index of the added file object in the specification's file list.

        """
        self.database.put(fileobj)
        return len(self.spec.files) - 1

    def refresh_available_images(self):
        """
        Refreshes the available_images dictionary.

        This method queries the database for BOLD files, extracts the entities
        and tags associated with them, and updates the available_images
        dictionary accordingly.

        """
        bold_filedict = {"datatype": "func", "suffix": "bold"}
        filepaths = self.database.get(**bold_filedict)

        db_entities, db_tags_set = self.database.multitagvalset(entities, filepaths=filepaths, min_set_size=0)
        logger.debug(f"UI->context->refresh_available_images:db_entities {db_entities}")
        logger.debug(f"UI->context->refresh_available_images:db_tags_set {db_tags_set}")
        extracted_entities = []
        options = []
        tagval_by_str = {}
        values = []
        for entity, tagvals_list in zip(db_entities, zip(*db_tags_set, strict=False), strict=False):
            if entity == "sub":
                continue

            tagvals_set = set(tagvals_list)
            if 1 < len(tagvals_set) < 16:
                extracted_entities.append(entity)

                entity_str = entity
                if entity_str in entity_display_aliases:
                    entity_str = entity_display_aliases[entity_str]
                entity_str = humanize(entity_str)
                options.append((entity_str, entity_colors[entity]))

                if None in tagvals_set:
                    tagvals_set.remove(None)

                tagvals = sorted(list(tagvals_set))

                row = [f'"{tagval}"' for tagval in tagvals]
                values.append(row)

                tagval_by_str.update(dict(zip(row, tagvals, strict=False)))

        self.available_images = {
            opt[0].lower(): [v.strip('"') for v in vals] for opt, vals in zip(options, values, strict=True)
        }

        logger.debug(f"UI->context->refresh_available_images:extracted_entities {extracted_entities}")
        logger.debug(f"UI->context->refresh_available_images:options {options}")
        logger.debug(f"UI->context->refresh_available_images:tagval_by_str {tagval_by_str}")
        logger.debug(f"UI->context->refresh_available_images:values {values}")
        logger.debug(f"UI->context->refresh_available_images:available_images  {self.available_images}")

    @property
    def get_available_images(self):
        """
        Returns the available_images dictionary.

        Returns
        -------
        dict
            A dictionary containing available images, keyed by entity type.
        """
        return self.available_images


ctx = Context()
