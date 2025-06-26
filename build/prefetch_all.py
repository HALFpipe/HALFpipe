#!/usr/bin/env python
import sys
import argparse
from pathlib import Path
from typing import Set, List, Dict, Optional

from conda.cli.python_api import run_command
from conda_build.api import render

def prefetch_all(recipes_dir: str, channels: Optional[List[str]] = None, numpy_version: Optional[str] = None, ignore_dirs: Optional[List[str]] = None):
    print(f"finding for recipes in directory: {recipes_dir}")
    
    recipes_path_obj = Path(recipes_dir).resolve()

    recipe_files = list(recipes_path_obj.rglob('meta.yaml'))

    if ignore_dirs:
        print(f"ignoring recipes in directories named: {', '.join(ignore_dirs)}")
        original_count = len(recipe_files)
        filtered_files = []
        for recipe_file in recipe_files:

            relative_path = recipe_file.parent.relative_to(recipes_path_obj)

            if not any(part in ignore_dirs for part in relative_path.parts):
                filtered_files.append(recipe_file)

        recipe_files = filtered_files
        print(f"filtered {original_count - len(recipe_files)} recipes. {len(recipe_files)} recipes remaining.")

    if not recipe_files:
        print("no recipes found (or all were ignored). Exiting.")
        return

    print(f"{len(recipe_files)} recipes to process.")

    variants: Dict[str, str] = {}
    if numpy_version:
        variants['numpy'] = numpy_version
        print(f"pinning numpy version to: {numpy_version} for dependency resolution.")

    all_deps: Set[str] = set()

    for recipe_file in recipe_files:
        recipe_path = str(recipe_file.parent)
        print(f"processing dependencies for: {recipe_path}")
        try:
            metadata_tuples = render(recipe_path,
                                     channels=channels or [],
                                     permit_unsatisfiable_variants=False,
                                     variants=variants)

            for m, _, _ in metadata_tuples:
                build_deps = m.get_value('requirements/build', [])
                host_deps = m.get_value('requirements/host', [])

                if build_deps:
                    all_deps.update(build_deps)
                if host_deps:
                    all_deps.update(host_deps)

        except Exception as e:
            print(f"could not process recipe {recipe_path}. skipping error: {e}", file=sys.stderr)
            continue
            
    if not all_deps:
        print("no dependencies to pre-fetch across all recipes.")
        return

    print(f"found {len(all_deps)} unique dependencies across all recipes to download.")


    install_args = ["install", "--download-only", "--yes"]
    if channels:
        for channel in channels:
            install_args.extend(["-c", channel])

    # Add all unique dependencies to the command.
    install_args.extend(sorted(list(all_deps)))

    print(f"running bulk dependency download")
    try:
        stdout, stderr, return_code = run_command(*install_args)
        if return_code != 0:
            print(f"error during bulk dependency download:\n{stderr}", file=sys.stderr)
            sys.exit(return_code)
        print("bulk dependency download successful.")
    except Exception as e:
        print(f"an exception occurred during bulk dependency download: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prefetch all conda build dependencies from a directory of recipes.")
    parser.add_argument("recipes_dir", help="Path to the directory containing recipe subdirectories.")
    parser.add_argument("-c", "--channel", action="append", help="Additional channel to search for dependencies.")
    parser.add_argument("--numpy-version", help="Version of numpy to pin during dependency resolution.")
    parser.add_argument("--ignore-dir", action="append", help="Directory name to ignore. Can be specified multiple times.")
    args = parser.parse_args()
    
    prefetch_all(args.recipes_dir, args.channel, args.numpy_version, args.ignore_dir)
