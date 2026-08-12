# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from hashlib import sha1
from pathlib import Path
from typing import Any, Iterable, overload

from ..logging import logger
from ..model.file.base import File
from ..model.spec import Spec
from ..model.tags import entities
from .metadata.loader import MetadataLoader
from .resolve import ResolvedSpec


class Database:
    def __init__(self, spec: Spec | ResolvedSpec, bids_database_dir: Path | None = None) -> None:
        resolved_spec = None
        if isinstance(spec, ResolvedSpec):
            logger.debug("Database.__init__: using provided ResolvedSpec")
            resolved_spec = spec
        elif isinstance(spec, Spec):
            logger.debug(
                "Database.__init__: resolving Spec (bids_database_dir=%s)",
                bids_database_dir,
            )
            resolved_spec = ResolvedSpec(spec, bids_database_dir=bids_database_dir)
        else:
            raise ValueError("Need to initialize Database with a Spec or ResolvedSpec")
        self.resolved_spec = resolved_spec

        self.metadata_loader = MetadataLoader(self)

        self.filepaths_by_tags: dict[str, dict[str, set[str]]] = dict()
        self.tags_by_filepaths: dict[str, dict[str, str]] = dict()

        logger.info(
            "Indexing %d resolved files",
            len(list(self.resolved_spec.resolved_files)),
        )

        for idx, file_obj in enumerate(self.resolved_spec.resolved_files, start=1):
            logger.debug(
                "Database.__init__: indexing file %d: %s",
                idx,
                file_obj.path,
            )
            self.index(file_obj)

        logger.info("Database initialization completed")

    def __hash__(self):
        return hash(tuple(self.tags_by_filepaths.keys()))

    @property
    def sha1(self):
        hash = sha1()
        for filepath in self.tags_by_filepaths.keys():
            hash.update(filepath.encode())
        return hash.hexdigest()

    def put(self, spec_fileobj):
        logger.debug("Database.put-> spec_fileobj.path=%s", spec_fileobj.path)

        resolved_files = self.resolved_spec.put(spec_fileobj)

        logger.debug(
            "Database.put-> resolved %d files from spec file",
            len(resolved_files),
        )

        for idx, resolved_fileobj in enumerate(resolved_files, start=1):
            logger.debug(
                "Database.put-> indexing resolved file %d/%d: %s",
                idx,
                len(resolved_files),
                resolved_fileobj.path,
            )
            self.index(resolved_fileobj)
            logger.debug(
                "Database.put-> resolved_fileobj.tags=%s",
                resolved_fileobj.tags,
            )

    def index(self, fileobj):
        logger.debug("Database.index-> start path=%s", fileobj.path)

        def add_tag_to_index(filepath, entity, tagval):
            if tagval is None:
                logger.debug(
                    "Database.index-> skip tag %s=None for %s",
                    entity,
                    filepath,
                )
                return

            logger.debug(
                "Database.index-> adding tag %s=%s for %s",
                entity,
                tagval,
                filepath,
            )

            if entity not in self.filepaths_by_tags:
                self.filepaths_by_tags[entity] = dict()
            tagvaldict = self.filepaths_by_tags[entity]

            if tagval not in tagvaldict:
                tagvaldict[tagval] = set()
            tagvaldict[tagval].add(filepath)

        filepath = fileobj.path

        tags = dict()
        if hasattr(fileobj, "tags"):
            tags = fileobj.tags

        tagdict = dict(datatype=fileobj.datatype)
        tagdict.update(tags)
        if hasattr(fileobj, "suffix"):
            tagdict.update(dict(suffix=fileobj.suffix))
        if hasattr(fileobj, "extension"):
            tagdict.update(dict(extension=fileobj.extension))

        logger.debug(
            "Database.index-> base tagdict=%s",
            tagdict,
        )

        self.tags_by_filepaths[filepath] = dict(**tagdict)

        # NB: field-map -> BOLD association is *not* encoded by rewriting tags. Files keep
        # their real tags; the association is resolved on demand via ``intended_for_targets``.
        for tagname, tagval in tagdict.items():
            add_tag_to_index(filepath, tagname, tagval)

        logger.debug("Database.index-> completed path=%s", filepath)

    def tags(self, filepath) -> dict[str, str] | None:
        """
        get a dictionary of entity -> value for a specific filepath
        """
        return self.tags_by_filepaths.get(filepath)

    def fileobj(self, filepath):
        return self.resolved_spec.fileobj(filepath)

    def specfileobj(self, filepath):
        return self.resolved_spec.specfileobj(filepath)

    def fromspecfileobj(self, specfileobj) -> list[File] | None:
        return self.resolved_spec.fromspecfileobj(specfileobj)

    @overload
    def tagval(
        self,
        filepath: list[str] | tuple[str, ...],
        entity: str,
    ) -> list[str | None]: ...

    @overload
    def tagval(
        self,
        filepath: str | Path,
        entity: str,
    ) -> str | None: ...

    def tagval(
        self,
        filepath: list[str] | tuple[str, ...] | str | Path,
        entity: str,
    ) -> str | list[str | None] | None:
        if isinstance(filepath, (list, tuple)):  # vectorize
            return [self.tagval(fp, entity) for fp in filepath]
        tagdict = self.tags_by_filepaths.get(str(filepath))
        if tagdict is not None:
            return tagdict.get(entity)
        else:
            return None

    def tagvaldict(self, entity):
        return self.filepaths_by_tags.get(entity)

    def get(self, **filters: str) -> set[str]:
        logger.debug("Database.get-> filters=%s", filters)

        res = None
        for tagname, tagval in filters.items():
            logger.debug(
                "Database.get-> applying filter %s=%s",
                tagname,
                tagval,
            )

            if tagname in self.filepaths_by_tags and tagval in self.filepaths_by_tags[tagname]:
                cur_set = self.filepaths_by_tags[tagname][tagval]
                if res is not None:
                    res &= cur_set
                else:
                    logger.debug(
                        "Database.get-> no matches for %s=%s",
                        tagname,
                        tagval,
                    )
                    res = cur_set.copy()
            else:
                res = None
                break

        logger.debug(f"Database.get-> result:{res}")
        if res is None:
            return set()
        return res

    def filter(self, filepaths, **filters: str) -> set[str]:
        logger.debug(
            "Database.filter-> start filepaths=%d filters=%s",
            len(filepaths),
            filters,
        )

        res = set(filepaths)

        for entity, tagval in filters.items():
            logger.debug(
                "Database.filter-> applying %s=%s",
                entity,
                tagval,
            )
            if entity not in self.filepaths_by_tags:
                logger.debug("Database.filter-> entity %s not indexed", entity)
                return set()
            if tagval not in self.filepaths_by_tags[entity]:
                logger.debug("Database.filter-> tagval %s not found for %s", tagval, entity)
                return set()
            cur_set = self.filepaths_by_tags[entity][tagval]
            res &= cur_set

        logger.debug(
            "Database.filter-> remaining=%d",
            len(res),
        )

        return res

    def applyfilters(self, filepaths: Iterable[str], filters: Any) -> set[str]:
        if not isinstance(filters, (tuple, list)) and hasattr(filters, "filters"):
            return self.applyfilters(filepaths, filters.filters)

        res = set(filepaths)

        for filter in filters:
            type = filter.get("type")
            if type == "tag":
                entity = filter.get("entity")
                assert entity in entities

                values = filter.get("values")
                assert isinstance(values, (list, tuple))

                filterset = set()
                for value in values:
                    filterset |= self.filter(filepaths, **{entity: value})

                action = filter.get("action")

                if action == "include":
                    res &= filterset
                elif action == "exclude":
                    res -= filterset
                else:
                    raise ValueError(f'Unsupported filter action "{action}"')

            else:
                raise ValueError(f'Unsupported filter type "{type}"')

        return res

    def tagvalset(self, entity, filepaths=None):
        if not isinstance(entity, str):
            return
        if entity not in self.filepaths_by_tags:
            return
        if filepaths is not None:
            if not isinstance(filepaths, set):
                filepaths = set(filepaths)
            return set(
                tagval
                for tagval, tagvalfilepaths in self.filepaths_by_tags[entity].items()
                if not filepaths.isdisjoint(tagvalfilepaths)
            )
        else:
            return set(self.filepaths_by_tags[entity].keys())

    def multitagvalset(self, entitylist, filepaths=None, prune=True, min_set_size=1):
        # Tomas added this: min_set_size because in the new UI in a special case when there is just one task
        # the output of this function is just empty list and hence there are no images for the selection panel
        # and everything then breaks. In the new UI this value is overridden to '0'.
        if prune:
            pruned_entitylist = []
            for entity in entitylist:
                tagval_set = self.tagvalset(entity, filepaths=filepaths)
                if tagval_set is not None and len(tagval_set) > min_set_size:
                    pruned_entitylist.append(entity)
            entitylist = pruned_entitylist

        if filepaths is None:
            filepaths = self.tags_by_filepaths.keys()

        return (
            entitylist,
            set(
                tuple(self.tags_by_filepaths[filepath].get(entity) for entity in entitylist)
                for filepath in filepaths
                if filepath in self.tags_by_filepaths
            ),
        )

    def fillmetadata(self, key: str, filepaths: Iterable[str]):
        found = False
        found_all = True
        for filepath in filepaths:
            fileobj = self.fileobj(filepath)
            if fileobj is None:
                raise ValueError(f'Unknown filepath "{filepath}"')
            found = self.metadata_loader.fill(fileobj, key)
            found_all = found_all and found
        return found

    def metadata(self, filepath, key):
        fileobj = self.fileobj(filepath)
        if fileobj is not None and hasattr(fileobj, "metadata"):
            if fileobj.metadata is not None and isinstance(fileobj.metadata, dict):
                return fileobj.metadata.get(key)
