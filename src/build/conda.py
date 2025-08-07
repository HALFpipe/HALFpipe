import asyncio
import os
from functools import cache
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Iterator

import boto3
import yaml
from botocore.exceptions import ClientError, NoCredentialsError
from conda_build.api import get_output_file_paths
from conda_build.build import clean_build
from conda_build.config import Config
from conda_build.metadata import MetaData, MetaDataTuple
from loguru import logger
from rattler.index import index_fs, index_s3
from setuptools_scm import get_version
from tqdm.auto import tqdm

base_path = Path("recipes").absolute()
build_path = Path("conda-bld").absolute()

with (base_path / "conda_build_config.yaml").open() as file_handle:
    config = Config(**yaml.safe_load(file_handle), croot=build_path)

s3_bucket = "conda-packages"
endpoint_url = os.environ.get("AWS_ENDPOINT_URL", None)
s3_client = boto3.client(
    "s3",
    endpoint_url=endpoint_url,
    region_name="auto",
    config=boto3.session.Config(s3={"addressing_style": "path"}),
)


def get_keys(metadata: MetaData) -> Iterator[tuple[Path, str]]:
    for output in get_output_file_paths(metadata):
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        s3_key = str(output_path.relative_to(build_path))
        yield output_path, s3_key


def download(metadata: MetaData) -> bool:
    for output_path, s3_key in get_keys(metadata):
        if output_path.is_file():
            continue
        try:
            s3_client.download_file(s3_bucket, s3_key, output_path)
            continue
        except (ClientError, NoCredentialsError) as error:
            if hasattr(error, "response") and error.response["Error"]["Code"] == "404":
                logger.info("Not found in registry:")
            else:
                logger.opt(exception=error).error("Cannot access registry:")
        return False
    return True


def build(metadata: MetaData) -> None:
    from conda_build.api import build as conda_build

    package_metadata = metadata.meta["package"]
    name = package_metadata["name"]
    try:
        logger.info(f"Starting build for {name}")
        conda_build(metadata, config=config)
        logger.info(f"Build successful for {name}")
    except Exception as exception:
        logger.opt(exception=exception).error(f'Build failed for "{name}"')


def exists(s3_key: str) -> bool:
    try:
        s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
        return True
    except ClientError as error:
        if hasattr(error, "response") and error.response["Error"]["Code"] == "404":
            return False
        raise error


def upload(metadata: MetaData) -> None:
    if os.environ.get("PUSH", "false") != "true":
        return
    for output_path, s3_key in get_keys(metadata):
        try:
            if exists(s3_key):
                return
            logger.info(f'Uploading {output_path} to registry at "{s3_key}"')
            s3_client.upload_file(output_path, s3_bucket, s3_key)
            logger.info(f'Upload complete for "{s3_key}"')
        except Exception as exception:
            logger.opt(exception=exception).error(f'Upload failed for "{s3_key}"')


@cache
def render(recipe_path: Path, permit_unsatisfiable_variants: bool = True) -> list[MetaDataTuple]:
    from conda_build.api import render as conda_render

    return conda_render(
        recipe_path=recipe_path,
        config=config,
        permit_unsatisfiable_variants=permit_unsatisfiable_variants,
        finalize=True,
    )


def get_name_to_recipe_path_map(recipe_paths: list[Path]) -> dict[str, Path]:
    name_to_recipe_path_map: dict[str, Path] = dict()
    for recipe_path in tqdm(recipe_paths, leave=False, desc="Finding package names"):
        metadata_tuples = render(recipe_path=recipe_path)
        for metadata, _, _ in metadata_tuples:
            name_to_recipe_path_map[metadata.name()] = recipe_path
    return name_to_recipe_path_map


def get_topological_sorter(name_to_recipe_path_map: dict[str, Path]) -> TopologicalSorter:
    recipe_paths = set(name_to_recipe_path_map.values())

    topological_sorter = TopologicalSorter()
    for recipe_path in tqdm(recipe_paths, leave=False, desc="Listing dependencies"):
        metadata_tuples = render(recipe_path=recipe_path)

        parent_recipe_paths: set[Path] = set()
        for metadata, _, _ in metadata_tuples:
            for requirement_type in {"build", "host", "run"}:
                for requirement in metadata.get_value(f"requirements/{requirement_type}") or list():
                    if requirement in name_to_recipe_path_map:
                        parent_recipe_paths.add(name_to_recipe_path_map[requirement])

        parent_recipe_paths.discard(recipe_path)
        topological_sorter.add(recipe_path, *parent_recipe_paths)
    return topological_sorter


async def main() -> None:
    logger.info(f'Gathering all recipes in "{base_path}"')
    recipe_paths = [recipe_meta_path.parent for recipe_meta_path in base_path.rglob("meta.yaml")]
    logger.debug(f"Found {len(recipe_paths)} total recipes")

    name_to_recipe_path_map = get_name_to_recipe_path_map(recipe_paths)
    topological_sorter = get_topological_sorter(name_to_recipe_path_map)
    logger.info("Build order found")

    topological_sorter.prepare()
    while recipe_paths := topological_sorter.get_ready():
        for recipe_path in tqdm(recipe_paths, leave=False, desc="Building recipes"):
            metadata_tuples = render(recipe_path=recipe_path, permit_unsatisfiable_variants=False)
            for metadata, _, _ in metadata_tuples:
                package_metadata = metadata.meta["package"]
                name = package_metadata["name"]
                if package_metadata["version"] in {"unknown"}:
                    version = get_version()
                    logger.info(f'Updating version for "{name}" to "{version}"')
                    package_metadata["version"] = version
                if not download(metadata):
                    build(metadata)
                upload(metadata)
                clean_build(config)
            topological_sorter.done(recipe_path)
        await index_fs(channel_directory=build_path, write_zst=False, write_shards=False)

    await index_s3(channel_url=f"s3://{s3_bucket}", region="auto", endpoint_url=endpoint_url)


if __name__ == "__main__":
    asyncio.run(main())
