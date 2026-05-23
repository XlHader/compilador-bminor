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

examples=(
	"$EXAMPLES_DIR/opt1.bminor"
	"$EXAMPLES_DIR/opt2.bminor"
	"$EXAMPLES_DIR/opt3.bminor"
	"$EXAMPLES_DIR/opt4.bminor"
)
levels=(-O0 -O1 -O2)
failures=0

print_rule() {
	printf '%*s\n' 78 '' | tr ' ' '='
}

print_subrule() {
	printf '%*s\n' 78 '' | tr ' ' '-'
}

for file in "${examples[@]}"; do
	if [[ ! -f "$file" ]]; then
		printf 'Missing example: %s\n' "$file"
		failures=$((failures + 1))
		continue
	fi

	name="$(basename "$file")"
	print_rule
	printf ' Example: %s\n' "$name"
	print_rule

	for level in "${levels[@]}"; do
		output_file="$(mktemp)"

		printf '\n'
		print_subrule
		printf ' %s | %s\n' "$name" "$level"
		print_subrule

		PYTHONPATH="$ROOT_DIR/src" "$PYTHON_BIN" -m proyect.main "$file" \
			--ir --no-tree "$level" >"$output_file" 2>&1
		status=$?

		printf ' exit code: %d\n\n' "$status"
		cat "$output_file"
		printf '\n'

		if [[ $status -ne 0 ]]; then
			failures=$((failures + 1))
		fi

		rm -f "$output_file"
	done

	printf '\n'
done

print_rule
if [[ $failures -eq 0 ]]; then
	printf ' All optimizer examples completed successfully.\n'
else
	printf ' Optimizer example failures: %d\n' "$failures"
fi
print_rule

if [[ $failures -ne 0 ]]; then
	exit 1
fi

exit 0
