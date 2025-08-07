import json
import os

from github import Github

from .. import __version__

github_context = json.loads(os.environ["GITHUB_CONTEXT"])

pushed_at = github_context["event"]["repository"]["pushed_at"]
ref = github_context["ref"]
repository = github_context["repository"]
sha = github_context["sha"]
url = github_context["event"]["repository"]["html_url"]
token = github_context["token"]

registry = os.environ["REGISTRY"]

repository_data = Github(token).get_repo(repository)
repository_owner, repository_name = repository.lower().split("/")
reference, type, name = ref.split("/")[:3]
if reference != "refs":
    raise ValueError(f"Unknown reference: {reference}")
if type == "heads":
    tag = {"main": "latest"}.get(name, name)
    push = True
elif type == "tags":
    tag = name
    push = True
elif type == "pull":
    tag = f"{type}-{name}"
    push = False
else:
    raise ValueError(f"Unknown reference type: {type}")

path = f"{registry}/{repository_name}"
cache_from = f"type=registry,ref={path}:buildcache"
output = dict(
    cache_from=cache_from,
    cache_to=f"{cache_from},compression=zstd,mode=max,ignore-error=true" if push else "",
    labels=[
        f'org.opencontainers.image.created="{pushed_at}"',
        'org.opencontainers.image.authors="Lea Waller <lea@fmri.science>"',
        f'org.opencontainers.image.url="{url}"',
        f'org.opencontainers.image.documentation="{url}"',
        f'org.opencontainers.image.source="{url}"',
        f'org.opencontainers.image.version="{__version__}"',
        f'org.opencontainers.image.revision="{sha}"',
        f'org.opencontainers.image.licenses="{repository_data.license.spdx_id}"',
        f'org.opencontainers.image.title="{repository_name}"',
        f'org.opencontainers.image.description="{repository_data.description}"',
    ],
    push=str(push).lower(),
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
