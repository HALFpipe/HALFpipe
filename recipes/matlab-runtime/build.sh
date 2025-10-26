#!/bin/bash

set -euo pipefail

install_path="$(pwd)/build"
mkdir --parents "${install_path}"

cat <<EOF >./installer-input.txt
mode=silent
destinationFolder=${install_path}
agreeToLicense=yes
product.MATLAB Runtime - Core
product.MATLAB Runtime - Graphics
product.MATLAB Runtime - Numerics
product.MATLAB Runtime - Non Interactive MATLAB
EOF

./install -inputFile ./installer-input.txt

find "${install_path}" -type f -name "*.dbg" -delete

MCRROOT=$(dirname "$(find "${install_path}" -type d -name "mcr" -print -quit)")
target_path="${PREFIX}/lib/mcr"

cp --no-dereference --preserve=links --no-preserve=mode,ownership --recursive \
    "${MCRROOT}/." "${target_path}"
