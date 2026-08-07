# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from pathlib import Path

resources: dict[str, Path] = {}


def register(base: Path) -> None:
    """Index every file below ``base`` by its base name."""
    for path in base.rglob("*"):
        if path.is_file() or path.is_symlink():
            resources[path.name] = path


# Resources are tracked with git-annex in the DataLad dataset and fetched
# lazily by ``halfpipe.resource.get``.
data_dir = Path(__file__).parent / "data"
register(data_dir)


def get(file_name: str | Path) -> str:
    path = resources.get(Path(file_name).name)
    if path is None:
        raise ValueError(f"Resource {file_name} not found")

    # A broken symlink means the git-annex content has not been fetched yet.
    # Real files (e.g. from a wheel install) or already-fetched content pass
    # through untouched. datalad is imported lazily so that importing this
    # module does not require it.
    if not path.is_file():
        import datalad.api as dl
        from datalad.utils import get_dataset_root

        dataset = get_dataset_root(path)
        dl.get(path, dataset=dataset)

    return str(path)
