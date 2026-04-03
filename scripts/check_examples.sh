#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXAMPLES_DIR="$ROOT_DIR/examples"

if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
    PYTHON_BIN="python"
fi

good_passed=0
bad_failed=0
failures=0

for file in "$EXAMPLES_DIR"/*.bminor; do
    [[ -e "$file" ]] || continue

    name="$(basename "$file")"
    output_file="$(mktemp)"

    PYTHONPATH="$ROOT_DIR/src" "$PYTHON_BIN" -m proyect.main "$file" \
        --no-tree >"$output_file" 2>&1
    status=$?

    if [[ "$name" == good* ]]; then
        if [[ $status -eq 0 ]]; then
            good_passed=$((good_passed + 1))
        else
            failures=$((failures + 1))
            printf 'FAIL good: %s\n' "$name"
            cat "$output_file"
        fi
    elif [[ "$name" == bad* ]]; then
        if [[ $status -ne 0 ]]; then
            bad_failed=$((bad_failed + 1))
            printf 'BAD expected failure: %s\n' "$name"
            cat "$output_file"
        else
            failures=$((failures + 1))
            printf 'FAIL bad: %s\n' "$name"
            cat "$output_file"
        fi
    fi

    rm -f "$output_file"
done

printf 'good files passed: %d\n' "$good_passed"
printf 'bad files failed as expected: %d\n' "$bad_failed"

if [[ $failures -ne 0 ]]; then
    printf 'unexpected example results: %d\n' "$failures"
    exit 1
fi

exit 0
