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

container=$(docker run \
    --detach \
    --rm \
    --workdir="/src" \
    --mac-address="${mac_address}" \
    --entrypoint="tail" \
    fmri.science/matlab-compiler \
    --follow /dev/null)

docker cp "compile.m" "${container}:/src"
docker cp "GroupICAT" "${container}:/src"
docker cp "${HOME}/license.lic" "${container}:/opt/matlab/license.lic"

docker exec --user="root" "${container}" chown --recursive matlab "/src" "/opt/matlab"

docker exec \
    --interactive \
    --env="MLM_LICENSE_FILE=/opt/matlab/license.lic" \
    "${container}" \
    matlab -batch "compile"

docker cp "${container}:/src/gica_cmdstandaloneApplication/gica_cmd" "${PREFIX}/bin/gica_cmd"

docker kill "${container}"
