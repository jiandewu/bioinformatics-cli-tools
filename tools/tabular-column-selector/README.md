# Tabular Column Selector

Select or remove columns from a delimited text table using exact header names.
The command is dependency-free, preserves the input column order, understands
quoted fields, and checks for missing columns and malformed rows.

## Quick start

Create a file containing one header name per line:

```text
sample_id
score
```

Keep those columns from a tab-separated table:

```bash
python select_columns.py columns.txt input.tsv > selected.tsv
```

Remove them instead:

```bash
python select_columns.py --exclude columns.txt input.tsv > reduced.tsv
```

For CSV input, specify the delimiter:

```bash
python select_columns.py --delimiter comma columns.txt input.csv > selected.csv
```

Use `-` as the input table to read from standard input. Blank lines and lines
starting with `#` in the names file are ignored. Missing headers are errors by
default; pass `--allow-missing` to ignore them.

## Environment

Only Python 3.10 or newer is required. An optional Conda environment is included:

```bash
conda env create -f environment.yml
conda activate tabular-column-selector
```

## Tests

```bash
python -m unittest discover -s tests -v
```

The repository contains code only. Input tables and generated results are not
tracked.
