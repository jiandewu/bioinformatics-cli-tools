# Delimited Table Transformer

A dependency-free Python CLI for recurring CSV and TSV transformations. It
replaces several one-off AWK scripts with consistent parsing, quoted-field
support, explicit errors, and tests.

## Commands

- `transpose`: exchange rows and columns.
- `swap-columns`: swap two columns by 1-based position.
- `swap-rows`: swap two rows by 1-based position.
- `unique-fields`: remove repeated values within each row while preserving order.
- `match-columns`: keep the first column plus headers containing a substring.
- `aggregate`: group by a key column and sum all other numeric columns.

## Examples

```bash
python table_transform.py transpose input.tsv > transposed.tsv

python table_transform.py swap-columns input.tsv 2 5 > swapped.tsv

python table_transform.py match-columns input.tsv score > scores.tsv

python table_transform.py aggregate input.tsv \
  --key-column sample_id > totals.tsv
```

Tab is the default delimiter. CSV and custom single-character delimiters are
supported:

```bash
python table_transform.py transpose input.csv \
  --delimiter comma > transposed.csv
```

Use `-` as the input path to read from standard input. Run
`python table_transform.py COMMAND --help` for command-specific options.

## Environment

Only Python 3.10 or newer is required:

```bash
conda env create -f environment.yml
conda activate delimited-table-transformer
```

## Tests

```bash
python -m unittest discover -s tests -v
```

The repository tracks code only. Input tables and generated output should stay
outside version control.
