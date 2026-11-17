import json
import os
import subprocess
from datetime import datetime, timezone

from github import Github
from setuptools_scm import get_version

github_context = json.loads(os.environ["GITHUB_CONTEXT"])

pushed_at: str = str(github_context["event"]["repository"]["pushed_at"])
if pushed_at.isdigit():
    moment = datetime.fromtimestamp(int(pushed_at), tz=timezone.utc)
else:
    moment = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
created: str = moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

url: str = github_context["event"]["repository"]["html_url"]

ref: str = github_context["ref"]
repository: str = github_context["repository"]
sha: str = github_context["sha"]
token: str = github_context["token"]

registry = os.environ["REGISTRY"]

prefixes = (
    "src/",
    "recipes/",
    "tests/",
    "Dockerfile",
    "pyproject.toml",
    ".github/workflows/continuous_integration.yml",
)
repository_owner, repository_name = repository.lower().split("/")
reference, type, name = ref.split("/")[:3]
if reference != "refs":
    raise ValueError(f"Unknown reference: {reference}")
if type == "heads":
    tag = {"main": "latest"}.get(name, name)
    push = True
    run = True
elif type == "tags":
    tag = name
    push = True
    run = True
elif type == "pull":
    tag = f"{type}-{name}"
    push = False
    changed_files: list[str] = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD^1", "HEAD"],
        text=True,
    ).splitlines()
    run = any(file.startswith(prefixes) for file in changed_files)
else:
    raise ValueError(f"Unknown reference type: {type}")

repository_data = Github(token).get_repo(repository)
path = f"{registry}/{repository_name}"
cache_from = f"type=registry,ref={path}:buildcache"
output = dict(
    cache_from=cache_from,
    cache_to=f"{cache_from},compression=zstd,mode=max,ignore-error=true" if push else "",
    labels=[
        f'org.opencontainers.image.created="{created}"',
        'org.opencontainers.image.authors="Lea Waller <lea@fmri.science>"',
        f'org.opencontainers.image.url="{url}"',
        'org.opencontainers.image.documentation="https://fmri.science/halfpipe/"',
        f'org.opencontainers.image.source="{url}"',
        f'org.opencontainers.image.version="{get_version()}"',
        f'org.opencontainers.image.revision="{sha}"',
        f'org.opencontainers.image.licenses="{repository_data.license.spdx_id}"',
        f'org.opencontainers.image.title="{repository_name}"',
        f'org.opencontainers.image.description="{repository_data.description}"',
    ],
    push=str(push).lower(),
    run=str(run).lower(),
    build_tag=f"{repository_name}:{tag}",
    push_tags=[
        f"{path}:{tag}",
        f"docker.io/{repository_owner}/{repository_name}:{tag}",
    ]
    if push
    else [],
    singularity_name=f"{repository_name}-{tag}.sif",
)

with open(os.environ["GITHUB_OUTPUT"], "at") as file_handle:
    for key, value in output.items():
        if isinstance(value, list):
            file_handle.write("\n".join([f"{key}<<eof", *value, "eof"]) + "\n")
        else:
            file_handle.write(f"{key}={value}\n")
