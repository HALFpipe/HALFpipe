#!/usr/bin/env bash

opts=$(getopt -o r: --long requirements-file: -n 'enigma-qc' -- "$@")
eval set -- "$opts"

verbose=1

requirements_files=()

fail() {
    printf '%s\n' "$1" >&2
    exit "${2-1}"
}

while true; do
    case "$1" in
    -r | --requirements-file)
        case "$2" in
        "") shift 2 ;;
        *)
            requirements_files+=("$2")
            shift 2
            ;;
        esac
        ;;
    --)
        shift
        break
        ;;
    *) fail "internal error!" ;;
    esac
done

if [[ "${#requirements_files[@]}" -lt 1 ]]; then
    fail "missing required --requirements-file parameter"
fi

run_cmd() {
    command="$*"

    printf '%s\n' --------------------

    if [ "${verbose}" = "1" ]; then
        printf "%s\n" "${command}"
    fi

    # shellcheck disable=SC2294
    eval "$@"

    exit_code=$?

    if [[ ${exit_code} -gt 0 ]]; then
        echo "ERROR: command exited with nonzero status ${exit_code}"
    fi

    printf '%s\n' --------------------

    return ${exit_code}
}

conda_packages=()

while read -r requirement; do
    if [ -z "${requirement}" ]; then
        continue
    fi

    printf '%s\n' --------------------

    requirement_variations=(
        "${requirement}"
        "${requirement//-/_}"
        "${requirement//-/.}"
    )
    mapfile -t requirement_variations < <(
        printf "%s\n" "${requirement_variations[@]}" | sort -u
    )
    echo "Checking package ${requirement_variations[0]}"
    if [ ${#requirement_variations[@]} -gt 1 ]; then
        echo "Also checking name variations" "${requirement_variations[@]:1}"
    fi

    for requirement_variation in "${requirement_variations[@]}"; do
        if run_cmd "mamba install --dry-run  --use-local \"${requirement_variation}\""; then
            printf 'Using mamba for package "%s"\n' "${requirement_variation}"
            conda_packages+=("${requirement_variation}")
            break
        fi
    done

    printf '%s\n' --------------------

done < <(grep --no-filename -v '#' "${requirements_files[@]}")

if ! run_cmd mamba install --yes --use-local "${conda_packages[@]}"; then
    exit 1
fi
