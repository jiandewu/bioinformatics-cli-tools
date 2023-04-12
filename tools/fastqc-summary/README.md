# FastQC summary CLI

A dependency-free Python command-line utility that extracts selected metrics from multiple FastQC ZIP archives or `fastqc_data.txt` reports and writes one TSV table.

## Metrics

The output contains:

- original filename;
- total and filtered sequence counts;
- sequence length;
- overall GC percentage;
- FastQC status for the Per base sequence quality module;
- percentage of sequencing-cycle positions whose reported mean quality is at least Q20;
- percentage of sequencing-cycle positions whose reported mean quality is at least Q30.

Grouped FastQC position ranges such as `10-14` are weighted by their number of positions.

The last two columns are deliberately named `cycle_percent_mean_q20` and `cycle_percent_mean_q30`. FastQC reports summary distributions at each sequencing position, so these values are not the percentage of all individual bases with Q20 or Q30 quality.

## Environment

The program uses only the Python standard library:

```bash
conda env create -f environment.yml
conda activate fastqc-summary-cli
```

## Usage

Write the table to standard output:

```bash
python fastqc_summary.py sample1_fastqc.zip sample2_fastqc.zip
```

Write it to a file:

```bash
python fastqc_summary.py \
  sample1_fastqc.zip sample2_fastqc.zip \
  --output results/summary.tsv
```

Inputs may be FastQC ZIP archives, extracted FastQC directories, or individual `fastqc_data.txt` files.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests use generated fixtures and do not contain sequencing data.

## Data policy

FastQC archives, extracted reports, sequencing data, generated summaries, manuscripts, drafts, and credentials are ignored by Git.
