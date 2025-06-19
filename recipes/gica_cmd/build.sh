#!/bin/bash

set -x
set -e

cat <<EOF >compile.m
addpath(genpath('GroupICAT/icatb'));

app_file = fullfile(which('gica_cmd'));
compiler.build.standaloneApplication(app_file);

exit;
EOF

host_id=$(sed --quiet --regexp-extended "s/.*HOSTID=MATLAB_HOSTID=(.{12}):.*/\1/p" "${HOME}/license.lic" |
    sort | uniq)
# shellcheck disable=SC2001
mac_address=$(echo "${host_id}" | sed "s/..\B/&:/g")

docker run \
    --detach \
    --rm \
    --name="build" \
    --workdir="/src" \
    --mac-address="${mac_address}" \
    --entrypoint="tail" \
    matlab-compiler \
    --follow /dev/null

docker cp "compile.m" "build:/src"
docker cp "GroupICAT" "build:/src"
docker cp "${HOME}/license.lic" "build:/opt/matlab/license.lic"

docker exec --user="root"  "build" chown --recursive matlab "/src" "/opt/matlab"

docker exec \
    --interactive \
    --env="MLM_LICENSE_FILE=/opt/matlab/license.lic" \
    "build" \
    matlab -batch "compile"

docker cp "build:/src/gica_cmdstandaloneApplication/gica_cmd" "${PREFIX}/bin/gica_cmd"

docker kill "build"
