# Bioinformatics CLI Tools

A collection of small, focused command-line utilities for common
bioinformatics and tabular-data tasks. Each tool is self-contained and keeps
its own documentation, tests, and Conda environment.

## Tools

| Tool | Language | Purpose |
| --- | --- | --- |
| [FastQC summary](tools/fastqc-summary/) | Python | Summarize one or more FastQC reports as TSV. |
| [Volcano plot](tools/volcano-plot/) | R | Create configurable volcano plots from CSV or TSV results. |
| [Genomic seqlevel converter](tools/genomic-seqlevel-converter/) | R | Convert genomic sequence naming styles in annotation files. |
| [Tabular column selector](tools/tabular-column-selector/) | Python | Keep or remove delimited-table columns by exact header name. |
| [Cell Ranger HDF5 utilities](tools/cellranger-hdf5-utils/) | R | Inspect and merge Cell Ranger feature-barcode HDF5 matrices. |

## Use a tool

Change to the tool directory and follow its README. For example:

```bash
cd tools/fastqc-summary
conda env create -f environment.yml
conda activate fastqc-summary-cli
python fastqc_summary.py --help
```

Environments are intentionally separate. This keeps the Python-only tools
lightweight and prevents the R/Bioconductor tools from forcing unrelated
dependencies into one large environment.

## Quick checks

The root check script runs Python unit tests, R syntax checks, and Shell syntax
checks without creating Conda environments:

```bash
./scripts/check.sh
```

Set `RSCRIPT` when `Rscript` is not on `PATH`:

```bash
RSCRIPT=/path/to/Rscript ./scripts/check.sh
```

Individual tool READMEs describe dependency-aware runtime or smoke tests.

## Repository scope

This repository is for compact, reusable utilities. Study-specific workflows,
data-source-specific analyses, research data, and generated results belong in
separate repositories.
