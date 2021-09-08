#!/usr/bin/env bash

OPTS=`getopt -o r: --long requirements-file: -n 'enigma-qc' -- "$@"`
eval set -- "$OPTS"

VERBOSE=1

REQUIREMENTS_FILES=()

fail() {
    printf '%s\n' "$1" >&2
    exit "${2-1}"
}

while true ; do
    case "$1" in
        -r|--requirements-file)
            case "$2" in
                "") shift 2 ;;
                *) REQUIREMENTS_FILES+=("$2") ; shift 2 ;;
            esac ;;
        --) shift ; break ;;
        *) fail "internal error!" ;;
    esac
done

if [[ "${#REQUIREMENTS_FILES[@]}" -lt 1 ]]; then
    fail "missing required --requirements-file parameter"
fi

run_cmd() {
    CMD="$*"

    if [ "$VERBOSE" = "1" ]; then
	    printf "$CMD\n"
    fi

    eval "$@"

    EXIT_CODE=$?
    return $EXIT_CODE
}

printf '%s\n' --------------------

# update conda and disable mkl
run_cmd conda install --yes --quiet "conda" "nomkl"

printf '%s\n' --------------------

run_cmd conda install --yes --quiet --channel "conda-forge" "pip" "gdb"

printf '%s\n' --------------------

CONDA_PACKAGES=()
PIP_PACKAGES=()

for R in $(grep -v '#' ${REQUIREMENTS_FILES[@]}); do

    printf '%s\n' --------------------

    if run_cmd "conda install --dry-run \"${R}\""; then
        printf 'using conda for package "%s"\n' "${R}"
        CONDA_PACKAGES+=("${R}")
    else
        printf 'using pip for package "%s"\n' "${R}"
        PIP_PACKAGES+=("${R}")
    fi

    printf '%s\n' --------------------
done

run_cmd conda install --yes ${CONDA_PACKAGES[@]}
run_cmd pip install ${PIP_PACKAGES[@]}
