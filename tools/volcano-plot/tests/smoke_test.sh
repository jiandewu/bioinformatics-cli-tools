#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT HUP INT TERM

test_rscript=${RSCRIPT:-Rscript}

printf 'feature\tlogFC\tadj.P.Val\nA\t3.0\t0.0001\nB\t-2.5\t0.0005\nC\t0.2\t0.8\n' \
  > "$test_dir/input.tsv"

"$test_rscript" "$project_dir/volcano_plot.R" \
  --input "$test_dir/input.tsv" \
  --output "$test_dir/volcano.png" \
  --title "Synthetic smoke test"

test -s "$test_dir/volcano.png"
printf 'Smoke test passed: non-empty PNG created.\n'
