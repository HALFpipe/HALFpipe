#!/usr/bin/env bash

opts=$(getopt -o r: --long requirements-file: -n 'install-requirements' -- "$@")
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
pip_packages=()

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

    package_manager="none"
    for requirement_variation in "${requirement_variations[@]}"; do
        if run_cmd "mamba install --dry-run  --use-local \"${requirement_variation}\" >/dev/null"; then
            printf 'Using mamba for package "%s"\n' "${requirement_variation}"
            conda_packages+=("${requirement_variation}")
            package_manager="mamba"
            break
        fi
    done

    if [ "${package_manager}" = "none" ]; then
        printf 'Using pip for package "%s"\n' "${requirement}"
        pip_packages+=("\"${requirement}\"")
        package_manager="pip"
    fi

    printf '%s\n' --------------------

done < <(grep --no-filename -v '#' "${requirements_files[@]}")

if ! run_cmd mamba install --yes --use-local "${conda_packages[@]}"; then
    exit 1
fi
# We assume that all python dependencies have already been resolved by `pip-compile`,
# so there will be no conflicts when we ask `pip` to install them.
if [ ${#pip_packages[@]} -gt 1 ]; then
    if ! run_cmd pip install --no-deps "${pip_packages[@]}"; then
        exit 1
    fi
fi
