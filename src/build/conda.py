import asyncio
import os
import re
from functools import cache
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Iterator, Sequence

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from conda_build.api import build, get_output_file_paths
from conda_build.build import clean_build
from conda_build.config import Config
from conda_build.metadata import MetaDataTuple
from loguru import logger
from rattler.index import index_fs, index_s3
from setuptools_scm import get_version
from tqdm.auto import tqdm

base_path = Path("recipes").absolute()
build_path = Path("conda-bld").absolute()

config = Config(exclusive_config_files=[base_path / "conda_build_config.yaml"], croot=build_path, numpy="1.26")

s3_bucket = "conda-packages"
endpoint_url = os.environ.get("AWS_ENDPOINT_URL", None)
s3_client = boto3.client(
    "s3",
    endpoint_url=endpoint_url,
    region_name="auto",
    config=boto3.session.Config(s3={"addressing_style": "path"}),
)

push = os.environ.get("PUSH", "false") == "true"

os.environ["halfpipe_version"] = get_version()


@cache
def render(recipe_path: Path, finalize: bool = False, permit_unsatisfiable_variants: bool = True) -> list[MetaDataTuple]:
    from conda_build.api import render as conda_render

    return conda_render(
        recipe_path=recipe_path,
        config=config,
        permit_unsatisfiable_variants=permit_unsatisfiable_variants,
        finalize=finalize,
    )


def get_name_to_recipe_path_map(recipe_paths: Sequence[Path]) -> dict[str, Path]:
    name_to_recipe_path_map: dict[str, Path] = dict()
    for recipe_path in tqdm(recipe_paths, leave=False, desc="Finding package names"):
        metadata_tuples = render(recipe_path=recipe_path)
        for metadata, _, _ in metadata_tuples:
            name_to_recipe_path_map[metadata.name()] = recipe_path
    return name_to_recipe_path_map


def get_topological_sorter(name_to_recipe_path_map: dict[str, Path]) -> TopologicalSorter[Path]:
    recipe_paths = set(name_to_recipe_path_map.values())

    topological_sorter: TopologicalSorter[Path] = TopologicalSorter()
    for recipe_path in tqdm(recipe_paths, leave=False, desc="Listing dependencies"):
        metadata_tuples = render(recipe_path=recipe_path)

        parent_recipe_paths: set[Path] = set()
        for metadata, _, _ in metadata_tuples:
            for requirement_type in {"build", "host", "run"}:
                for requirement in metadata.get_value(f"requirements/{requirement_type}") or list():
                    requirement = re.split(r"[ =<>!~]", requirement, maxsplit=1)[0]
                    if requirement in name_to_recipe_path_map:
                        parent_recipe_paths.add(name_to_recipe_path_map[requirement])

        parent_recipe_paths.discard(recipe_path)
        topological_sorter.add(recipe_path, *parent_recipe_paths)
    return topological_sorter


def get_keys(metadata_tuples: list[MetaDataTuple]) -> Iterator[tuple[Path, str]]:
    for output in get_output_file_paths(metadata_tuples):
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        s3_key = str(output_path.relative_to(build_path))
        yield output_path, s3_key


def download(keys: list[tuple[Path, str]]) -> bool:
    for output_path, s3_key in keys:
        if output_path.is_file():
            continue
        try:
            s3_client.download_file(s3_bucket, s3_key, output_path)
            continue
        except (ClientError, NoCredentialsError) as error:
            if hasattr(error, "response") and error.response["Error"]["Code"] == "404":
                logger.info("Not found in registry")
            else:
                logger.opt(exception=error).error("Cannot access registry:")
        return False
    return True


def exists(s3_key: str) -> bool:
    try:
        s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
        return True
    except ClientError as error:
        if hasattr(error, "response") and error.response["Error"]["Code"] == "404":
            return False
        raise error


def upload(keys: list[tuple[Path, str]]) -> None:
    if not push:
        return
    for output_path, s3_key in keys:
        if not output_path.is_file():
            raise ValueError(f"Output path {output_path} is not a file")
        try:
            if exists(s3_key):
                return
            logger.info(f'Uploading {output_path} to registry at "{s3_key}"')
            s3_client.upload_file(output_path, s3_bucket, s3_key)
            logger.info(f'Upload complete for "{s3_key}"')
        except Exception as exception:
            logger.opt(exception=exception).error(f'Upload failed for "{s3_key}":')


async def main() -> None:
    logger.info(f'Gathering all recipes in "{base_path}"')
    recipe_paths = sorted(recipe_meta_path.parent for recipe_meta_path in base_path.rglob("meta.yaml"))
    logger.debug(f"Found {len(recipe_paths)} total recipes")

    name_to_recipe_path_map = get_name_to_recipe_path_map(recipe_paths)
    topological_sorter = get_topological_sorter(name_to_recipe_path_map)

    recipe_paths = list(topological_sorter.static_order())
    logger.info(f"Build order found: {[recipe_path.name for recipe_path in recipe_paths]}")
    for recipe_path in tqdm(recipe_paths, leave=False, desc="Building recipes"):
        name = recipe_path.name

        metadata_tuples = render(recipe_path=recipe_path, finalize=True, permit_unsatisfiable_variants=False)

        keys = list(get_keys(metadata_tuples))
        logger.debug(f'Found keys {[s3_key for _, s3_key in keys]} for "{name}"')

        if not download(keys):
            logger.info(f"Starting build for {name}")
            build(str(recipe_path), config=config)
            logger.info(f"Build successful for {name}")

        upload(keys)
        clean_build(config)

        await index_fs(channel_directory=build_path, write_zst=False, write_shards=False)

    if push:
        await index_s3(channel_url=f"s3://{s3_bucket}", region="auto", endpoint_url=endpoint_url)


if __name__ == "__main__":
    asyncio.run(main())
