import argparse
import asyncio
import os
import re
import subprocess
import sys
from graphlib import TopologicalSorter
from pathlib import Path

import boto3
import yaml
from botocore.exceptions import ClientError, NoCredentialsError
from conda_build.api import get_output_file_paths, render
from conda_build.config import Config
from loguru import logger

s3_client_failure = False


async def gather_all_rendered(build_config, recipes_dir, ignore_dir):
    logger.info(f"Gathering all rendered recipes in: {recipes_dir}")
    logger.debug(f"Ignoring directories: {ignore_dir}")
    all_dirs = [d for d in Path(recipes_dir).iterdir() if d.is_dir()]
    if ignore_dir:
        ignored = set(ignore_dir)
        filtered_dirs = [d for d in all_dirs if d.name not in ignored]
    else:
        filtered_dirs = all_dirs
    logger.debug(f"Found recipe directories: {[d.name for d in filtered_dirs]}")
    local_names = set()
    name_to_path_map = {}
    name_to_metadata_map = {}
    for package in filtered_dirs:
        try:
            render_args = {
                "recipe_path": str(package),
                "permit_unsatisfiable_variants": False,
            }

            if build_config:
                logger.debug("Using discovered build_config with render_args")
                render_args["config"] = build_config

            logger.debug(f"Rendering package {package.name}")
            metadata_list = render(**render_args)
            for metadata, _, _ in metadata_list:
                package_name = metadata.name()
                local_names.add(package_name)
                if package_name not in name_to_path_map:
                    name_to_path_map[package_name] = package
                    name_to_metadata_map[package_name] = metadata
        except Exception:
            logger.error(f"Error rendering {package.name}")
    return local_names, name_to_path_map, name_to_metadata_map


def build_dependency_graph(local_names, name_to_meta):
    logger.debug("Building dependency graph")
    dependency_graph = {}
    for package_name in name_to_meta:
        dependencies = set()
        build_reqs = name_to_meta[package_name].get_value("requirements/build", [])
        host_reqs = name_to_meta[package_name].get_value("requirements/host", [])
        run_reqs = name_to_meta[package_name].get_value("requirements/run", [])
        all_reqs = build_reqs + host_reqs + run_reqs

        for req in all_reqs:
            req_name = re.split(r"[ =<>!~]", req, 1)[0]  # noqa: B034
            if req_name in local_names and req_name != package_name:
                dependencies.add(req_name)
        dependency_graph[package_name] = dependencies
    return dependency_graph


def process_build_queue(build_order, name_to_path_map, name_to_metadata_map, args):
    """
    Processes the build queue, checking S3 before building and uploading after.
    """
    s3_client = boto3.client("s3", config=boto3.session.Config(s3={"addressing_style": "path"}))
    ## Use user-provided folder or conda-build's default build root
    build_root = Config().croot
    logger.debug(f"Using {build_root} for the build_root")

    for i, package_name in enumerate(build_order, 1):
        logger.info(f"Processing step {i}/{len(build_order)}: {package_name}")

        metadata = name_to_metadata_map.get(package_name)
        if not metadata:
            logger.error(f"Could not find metadata for {package_name}!")
            raise Exception()

        output_paths = get_output_file_paths(metadata)
        if not output_paths:
            logger.error(f"Could not determine output path for {package_name}.")
            raise Exception()

        local_file_path = output_paths[0]
        s3_key = os.path.relpath(local_file_path, build_root)
        package_filename = os.path.basename(local_file_path)
        # --- S3 Check ---
        s3_package_exists = False
        global s3_client_failure
        if (s3_client and not args.force_build) and not s3_client_failure:
            try:
                logger.debug(f"Local file path for: {package_name}: {local_file_path}")
                logger.debug(f"File's s3_key is: {s3_key}")
                logger.debug(f"Package's filename is: {package_filename}")
                s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
                s3_package_exists = True
                logger.info(f"Found in S3 s3://{s3_bucket}/{s3_key}")
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                logger.info(f"Downloading {package_filename}...")
                s3_client.download_file(s3_bucket, s3_key, local_file_path)
                logger.info("Download complete.")
            except (ClientError, NoCredentialsError) as e:
                if hasattr(e, "response") and e.response["Error"]["Code"] == "404":
                    logger.info(f"Not found in S3. Build required. {e}")
                else:
                    s3_client_failure = True
                    logger.error(f"AWS Error, must build package {package_name}: {e}")

        if s3_package_exists and not args.force_build:
            logger.info(f"{package_name} complete")
            continue

        recipe_path = name_to_path_map[package_name]
        logger.info(f"Building {package_name}")

        if not Path(local_file_path).exists():
            command = [
                "conda",
                "build",
                str(recipe_path),
                "--output-folder",
                build_root,
                "--no-anaconda-upload",
                "--numpy",
                args.numpy_version,
            ]
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                )
                stdout, _ = process.communicate()

                if process.returncode != 0:
                    logger.error(f"Build failed for {package_name}. Output:\n{stdout}")
                    raise subprocess.CalledProcessError(process.returncode, command, output=stdout)

                logger.debug(f"Build command output for {package_name}\n{stdout}")
                for line in re.split(r"\r\n|\r|\n", stdout):  # noqa: B034
                    logger.debug(f"{line}")
                logger.info(f"Build successful for {package_name}")

            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error(f"ERROR: Build failed for {package_name}.")
                logger.error("Aborting remaining builds.")
                return False
        else:
            logger.info(
                f"Found {local_file_path}; {package_name} likely an output from a parent package, and does not need built."
            )

        if not s3_client_failure:
            logger.info(f"Uploading {package_filename} to S3")
            try:
                s3_client.upload_file(local_file_path, s3_bucket, s3_key)
                logger.info(f"Upload complete for {package_filename}")
            except Exception as e:
                logger.error(f"ERROR: S3 upload failed for {package_filename}: {e}")
                return False
    return True


async def main():
    logger.info("Starting build")
    build_config = None
    if (Path(args.recipes_dir) / "conda_build_config.yaml").exists():
        logger.info("Using build config")
        with open(Path(args.recipes_dir) / "conda_build_config.yaml") as f:
            build_config = Config(**yaml.safe_load(f))
    local_names, name_to_path, name_to_meta = await gather_all_rendered(build_config, args.recipes_dir, args.ignore_dir)
    logger.debug(f"Found {len(local_names)} total local packages")
    dep_graph = build_dependency_graph(local_names, name_to_meta)
    try:
        ts = TopologicalSorter(dep_graph)
        build_order = list(ts.static_order())

        if args.verbose:
            dep_report = "Dependency Report\n"
            for i, pkg in enumerate(build_order, 1):
                deps = dep_graph.get(pkg)
                dep_report += f"  {i}. {pkg} (depends on: {list(deps) if deps else 'none'})\n"
            logger.debug(dep_report)
        logger.info("Build order found")
    except Exception as e:
        logger.error(f"Error during topological sort (circular dependency?): {e}")
        sys.exit(1)

    if args.build:
        logger.info("Building recipes")
        if process_build_queue(build_order, name_to_path, name_to_meta, args):
            logger.info("All builds completed successfully")
        else:
            logger.error("Build process failed")
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a recipe directory with optional S3 caching support")
    parser.add_argument("recipes_dir", help="Path to the directory containing recipe subdirectories.")
    parser.add_argument(
        "--ignore-dir",
        action="append",
        help="Directory name to ignore. Can be specified multiple times.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose (DEBUG) logging.")
    parser.add_argument(
        "--build",
        action="store_true",
        help="Execute the build process. If not set, print only the build order.",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Do not upload newly built packages to S3.",
    )
    parser.add_argument(
        "--force-build",
        action="store_true",
        help="Force building recipes even if they exist in the S3 cache.",
    )
    parser.add_argument(
        "--numpy-version",
        action="store_true",
        default="1.24",
        help="Sets the numpy version for conda build",
    )
    args = parser.parse_args()

    s3_bucket = os.getenv("CONDA_BUCKET") if os.getenv("CONDA_BUCKET") else "conda-packages"

    # Ensure 'halfpipe' is always in ignore_dir
    if args.ignore_dir is None:
        args.ignore_dir = []
    if "halfpipe" not in args.ignore_dir:
        args.ignore_dir.append("halfpipe")

    # Configure Loguru
    # libraries like boto and conda_build do not pickup this configuration.
    # ToDo: process the handler tree, and ensure imported libraries pickup our config (might be as simple as moving imports?)
    logger.remove()
    level = "DEBUG" if args.verbose else "INFO"
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
    )
    logger.add(sys.stdout, level=level, format=log_format)
    logger.debug("Parsed arguments.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Exiting gracefully.")
        sys.exit(1)
