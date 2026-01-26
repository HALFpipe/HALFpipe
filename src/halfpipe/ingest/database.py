# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from hashlib import sha1
from pathlib import Path
from typing import Iterable, Mapping

from ..logging import logger
from ..model.spec import Spec
from ..model.tags import entities
from .metadata.loader import MetadataLoader
from .resolve import ResolvedSpec


class Database:
    def __init__(self, spec: Spec | ResolvedSpec, bids_database_dir: Path | None = None) -> None:
        logger.info("Database initialization started")

        resolved_spec = None
        if isinstance(spec, ResolvedSpec):
            resolved_spec = spec
            logger.debug("Using pre-resolved spec")
        elif isinstance(spec, Spec):
            logger.debug("Resolving spec via ResolvedSpec")
            resolved_spec = ResolvedSpec(spec, bids_database_dir=bids_database_dir)
        else:
            raise ValueError("Need to initialize Database with a Spec or ResolvedSpec")
        self.resolved_spec = resolved_spec

        self.metadata_loader = MetadataLoader(self)
        self.filepaths_by_tags: dict[str, dict[str, set[str]]] = dict()
        self.tags_by_filepaths: dict[str, dict[str, str]] = dict()

        logger.info(f"Indexing {len(list(self.resolved_spec.resolved_files))} files from resolved spec")
        for file_obj in self.resolved_spec.resolved_files:
            self.index(file_obj)

    def __hash__(self):
        return hash(tuple(self.tags_by_filepaths.keys()))

    @property
    def sha1(self):
        hash = sha1()
        for filepath in self.tags_by_filepaths.keys():
            hash.update(filepath.encode())
        return hash.hexdigest()

    def put(self, spec_fileobj):
        logger.info(f"Database.put-> Adding spec file: {spec_fileobj.path}")
        resolved_files = self.resolved_spec.put(spec_fileobj)
        for resolved_fileobj in resolved_files:
            self.index(resolved_fileobj)
            logger.debug(f"Database.put-> Indexed file: {resolved_fileobj.path} tags={resolved_fileobj.tags}")
        logger.info(f"Database.put-> Completed for spec file: {spec_fileobj.path}")
        return resolved_files

    def index(self, fileobj):
        def add_tag_to_index(filepath, entity, tagval):
            if tagval is None:
                return
            if entity not in self.filepaths_by_tags:
                self.filepaths_by_tags[entity] = dict()
            if tagval not in self.filepaths_by_tags[entity]:
                self.filepaths_by_tags[entity][tagval] = set()
            self.filepaths_by_tags[entity][tagval].add(filepath)
            logger.debug(f"Database.index-> Added tag {entity}={tagval} for {filepath}")

        logger.debug(f"Database.index-> Indexing file: {fileobj.path}")
        filepath = fileobj.path
        tagdict = dict(datatype=fileobj.datatype)
        if hasattr(fileobj, "tags"):
            tagdict.update(fileobj.tags)
        if hasattr(fileobj, "suffix"):
            tagdict["suffix"] = fileobj.suffix
        if hasattr(fileobj, "extension"):
            tagdict["extension"] = fileobj.extension

        logger.debug(f"Database.index-> Initial tagdict for {filepath}: {tagdict}")

        self.tags_by_filepaths[filepath] = dict(tagdict)
        logger.debug(f"Database.index-> tags_by_filepaths updated for {filepath}")

        # handle IntendedFor mappings if present
        if hasattr(fileobj, "intended_for") and fileobj.intended_for:
            logger.debug(f"Database.index-> Processing intended_for for {filepath}")
            for from_entity_val, to_list in fileobj.intended_for.items():
                from_entity, from_tagval = from_entity_val.split(".")
                if from_tagval == "null":
                    from_tagval = None
                if tagdict.get(from_entity) != from_tagval:
                    continue
                if from_entity in tagdict:
                    del tagdict[from_entity]
                for v in to_list:
                    to_entity, to_tagval = v.split(".")
                    add_tag_to_index(filepath, to_entity, to_tagval)

        # finally, index the remaining tags
        for tname, tval in tagdict.items():
            add_tag_to_index(filepath, tname, tval)

        logger.info(f"Database.index-> Completed indexing file: {filepath}")

    def tags(self, filepath):
        """
        get a dictionary of entity -> value for a specific filepath
        """
        return self.tags_by_filepaths.get(filepath)

    def fileobj(self, filepath):
        return self.resolved_spec.fileobj(filepath)

    def specfileobj(self, filepath):
        return self.resolved_spec.specfileobj(filepath)

    def fromspecfileobj(self, specfileobj):
        return self.resolved_spec.fromspecfileobj(specfileobj)

    def tagval(self, filepath, entity):
        if isinstance(filepath, (list, tuple)):  # vectorized
            logger.debug(f"Database.tagval-> Vectorized call for entity={entity}, filepaths={filepath}")
            return [self.tagval(fp, entity) for fp in filepath]

    def tagvaldict(self, entity):
        result = self.filepaths_by_tags.get(entity)
        logger.debug(f"Database.tagvaldict-> entity={entity}, values={result}")
        return result

    def get(self, **filters: str) -> set[str]:
        logger.debug(f"Database.get-> filters={filters}")
        res = None
        for tagname, tagval in filters.items():
            if tagname in self.filepaths_by_tags and tagval in self.filepaths_by_tags[tagname]:
                cur_set = self.filepaths_by_tags[tagname][tagval]
                res = cur_set.copy() if res is None else res & cur_set
                logger.debug(f"Database.get-> tag {tagname}={tagval} matched {len(cur_set)} files")
            else:
                logger.debug(f"Database.get-> tag {tagname}={tagval} not found, returning empty set")
                return set()
        logger.debug(f"Database.get-> Resulting files: {res}")
        return res if res is not None else set()

    def associations(self, filepath: str, **filters: str) -> tuple[str, ...] | None:
        logger.debug(f"Database.associations-> Finding associations for {filepath} with filters {filters}")
        matching_files = self.get(**filters)
        logger.debug(f"Database.associations-> Initial matching_files={matching_files}")
        for entity in reversed(entities):
            if entity not in self.filepaths_by_tags:
                continue
            cur_set = set()
            for _, filepaths in self.filepaths_by_tags[entity].items():
                if filepath in filepaths:
                    cur_set |= filepaths
            cur_set &= matching_files
            logger.debug(f"Database.associations-> entity={entity}, cur_set={cur_set}")
            if len(cur_set) > 0:
                matching_files = cur_set
            if len(cur_set) == 1:
                break
        if matching_files:
            logger.debug(f"Database.associations-> Final associated files: {matching_files}")
            return tuple(matching_files)
        logger.debug("Database.associations-> No associations found")
        return None

    def associations2(self, optional_tags: Mapping[str, str], mandatory_tags: Mapping[str, str]) -> tuple[str, ...] | None:
        logger.debug(f"Database.associations2-> mandatory_tags={mandatory_tags}, optional_tags={optional_tags}")
        matching_files = self.get(**mandatory_tags)
        logger.debug(f"Database.associations2-> Initial matching_files={matching_files}")

        for entity in reversed(entities):
            if entity not in self.filepaths_by_tags:
                continue
            if entity not in optional_tags:
                continue
            entity_dict = self.filepaths_by_tags[entity]
            tagval = optional_tags[entity]
            if tagval not in entity_dict:
                logger.debug(f"Database.associations2-> entity {entity} does not have tagval {tagval}")
                continue
            files: set[str] = entity_dict[tagval].copy()
            logger.debug(f"Database.associations2-> entity={entity}, tagval={tagval}, files={files}")
            files &= matching_files
            logger.debug(f"Database.associations2-> entity={entity}, filtered files={files}")
            if files:
                matching_files = files
            if len(files) == 1:
                break

        if matching_files:
            logger.debug(f"Database.associations2-> Final associated files: {matching_files}")
            return tuple(matching_files)
        logger.debug("Database.associations2-> No associations found")
        return None

    def tagvalset(self, entity, filepaths=None):
        if not isinstance(entity, str):
            return
        if entity not in self.filepaths_by_tags:
            return

        if filepaths is not None:
            if not isinstance(filepaths, set):
                filepaths = set(filepaths)
            result = {
                tagval
                for tagval, filepaths_for_tag in self.filepaths_by_tags[entity].items()
                if not filepaths.isdisjoint(filepaths_for_tag)
            }
        else:
            result = set(self.filepaths_by_tags[entity].keys())

        logger.debug(f"Database.tagvalset-> entity={entity}, filepaths={filepaths}, result={result}")
        return result

    def multitagvalset(self, entitylist, filepaths=None, prune=True, min_set_size=1):
        # Tomas added this: min_set_size because in the new UI in a special case when there is just one task
        # the output of this function is just empty list and hence there are no images for the selection panel
        # and everything then breaks. In the new UI this value is overridden to '0'.
        if prune:
            pruned_entitylist = []
            for entity in entitylist:
                tagval_set = self.tagvalset(entity, filepaths=filepaths)
                if tagval_set and len(tagval_set) > min_set_size:
                    pruned_entitylist.append(entity)
            entitylist = pruned_entitylist
            logger.debug(f"Database.multitagvalset-> pruned entitylist={entitylist}")

        if filepaths is None:
            filepaths = self.tags_by_filepaths.keys()

        result_set = set(
            tuple(self.tags_by_filepaths[filepath].get(entity) for entity in entitylist)
            for filepath in filepaths
            if filepath in self.tags_by_filepaths
        )
        logger.debug(f"Database.multitagvalset-> result_set={result_set}")
        return entitylist, result_set

    def fillmetadata(self, key: str, filepaths: Iterable[str]):
        logger.debug(f"Database.fillmetadata-> key={key}, filepaths={filepaths}")
        found_all = True
        for filepath in filepaths:
            fileobj = self.fileobj(filepath)
            if fileobj is None:
                raise ValueError(f'Unknown filepath "{filepath}"')
            found = self.metadata_loader.fill(fileobj, key)
            found_all = found_all and found
            logger.debug(f"Database.fillmetadata-> file={filepath}, key={key}, found={found}")
        logger.debug(f"Database.fillmetadata-> All metadata found: {found_all}")
        return found_all

    def metadata(self, filepath, key):
        fileobj = self.fileobj(filepath)
        if fileobj is not None and hasattr(fileobj, "metadata") and isinstance(fileobj.metadata, dict):
            value = fileobj.metadata.get(key)
            logger.debug(f"Database.metadata-> filepath={filepath}, key={key}, value={value}")
            return value
        logger.debug(f"Database.metadata-> filepath={filepath}, key={key}, value=None")
        return None
