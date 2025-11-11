#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT_1="patch_profiles.py"
PYTHON_SCRIPT_2="patch_handlers.py"
PYTHON_SCRIPT_3="patch_subdriver.py"

usage() {
    cat <<EOF
Usage: ./auto_patch.sh [-n|--dry-run] [-v|--verbose] DriverName DeviceModel Manufacturer AttributeList

Positional arguments:
  DriverName      Folder name (or relative path) of the Edge driver to patch
  DeviceModel     Device's model string as reported by SmartThings
  Manufacturer    Device's manufacturer string as reported by SmartThings
  AttributeList   Colon separated list of attributes or ALL

Optional flags:
  -n, --dry-run   Preview all file operations without changing files
  -v, --verbose   Print verbose logging from helper scripts
  -h, --help      Show this help message
EOF
}

DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

if [[ "$#" -ne 4 ]]; then
    echo "ArgumentError: Illegal number of arguments."
    usage
    exit 1
fi

DRIVER_ARG=$1
MODEL_ARG=$2
MANUFACTURER_ARG=$3
ATTRIBUTES_ARG=$4
BACKUP_DIR="${DRIVER_ARG}-backup"

COMMON_ARGS=()
if [[ "${DRY_RUN}" == true ]]; then
    COMMON_ARGS+=("--dry-run")
fi
if [[ "${VERBOSE}" == true ]]; then
    COMMON_ARGS+=("--verbose")
fi

restore_backup() {
    if [[ "${DRY_RUN}" == true ]]; then
        exit 1
    fi
    echo "Restoring backup due to an error..."
    rm -rf "${DRIVER_ARG}"
    mv "${BACKUP_DIR}" "${DRIVER_ARG}"
    echo "Backup restored."
    exit 1
}

create_backup() {
    if [[ "${DRY_RUN}" == true ]]; then
        echo "[Dry run] Skipping backup creation for ${DRIVER_ARG}"
        return
    fi

    if [[ -d "${BACKUP_DIR}" ]]; then
        echo "Backup already exists at ${BACKUP_DIR}; it will be reused."
    else:
        echo "Creating driver backup at ${BACKUP_DIR}..."
        cp -r "${DRIVER_ARG}" "${BACKUP_DIR}"
    fi
}

cd "${SCRIPT_DIR}"
create_backup

echo "Running Step 1: Patching fingerprints..."
if ! python3 "${PYTHON_SCRIPT_1}" \
    --driver "${DRIVER_ARG}" \
    --model "${MODEL_ARG}" \
    --mfg "${MANUFACTURER_ARG}" \
    --attributes "${ATTRIBUTES_ARG}" \
    --config "${SCRIPT_DIR}/custom_capability_list.config" \
    "${COMMON_ARGS[@]}"; then
    echo "Error occurred in Step 1."
    restore_backup
fi

echo "Running Step 2: Patching handler functions..."
if ! python3 "${PYTHON_SCRIPT_2}" \
    --driver "${DRIVER_ARG}" \
    --config "${SCRIPT_DIR}/driver2patch.config" \
    "${COMMON_ARGS[@]}"; then
    echo "Error occurred in Step 2."
    restore_backup
fi

echo "Running Step 3: Patching subdriver..."
if ! python3 "${PYTHON_SCRIPT_3}" \
    --driver "${DRIVER_ARG}" \
    --model "${MODEL_ARG}" \
    --mfg "${MANUFACTURER_ARG}" \
    --config "${SCRIPT_DIR}/driver2patch.config" \
    "${COMMON_ARGS[@]}"; then
    echo "Error occurred in Step 3."
    restore_backup
fi

echo
echo "All steps completed successfully! <${DRIVER_ARG}> is now the patched driver!"
