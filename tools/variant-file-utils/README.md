# Variant file utilities

Dependency-free Python commands for compact variant/QC reporting and simple
VCF filtering. Inputs may be plain text or gzip-compressed.

## Environment

```bash
conda env create -f environment.yml
conda activate variant-file-utils
```

## Build a one-row QC summary

```bash
python variant_file_utils.py summary \
  --sample sample-01 \
  --vcf raw=sample.raw.vcf.gz \
  --vcf filtered=sample.filtered.vcf.gz \
  --depth sample.depth.tsv \
  --alignment-metrics sample.alignment_metrics.txt \
  --insert-metrics sample.insert_metrics.txt \
  --output sample.qc.tsv
```

Each `--vcf LABEL=PATH` produces `<label>_variants` and
`<label>_pass_variants`. The depth input uses the usual three-column
`CHROM POS DEPTH` format. Picard alignment and insert-size tables are optional.
Use `--format json` when machine-readable output is more convenient.

## Filter a VCF

```bash
python variant_file_utils.py filter-vcf calls.vcf.gz \
  --min-qual 30 --pass-only --output calls.filtered.vcf
```

Header lines are preserved. Records with missing QUAL are excluded when
`--min-qual` is specified. This command performs straightforward record-level
filtering; it is not a replacement for caller-specific recalibration or best
practices workflows.

## Summarize allele balance by genomic window

```bash
python variant_file_utils.py allele-balance calls.vcf.gz \
  --sample sample-01 \
  --window-size 1000000 \
  --min-depth 4 \
  --max-depth 79 \
  --min-variants 10 \
  --output sample-01.allele-balance.tsv
```

The command reads the VCF `FORMAT/AD` field and sums reference and all
alternate-allele depths in non-overlapping, one-based windows. It reports both
the alternate-read fraction and alternate/reference ratio. Repeat `--sample`
to select multiple samples; omit it to process every sample in the VCF.
Records without usable AD values or outside the depth range are skipped.

## Test

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

## Scope and privacy

This tool contains no study data, family/pedigree information, sample mappings,
server addresses, or project-specific pipelines. Do not commit VCF, BAM, CRAM,
BCF, or generated result files; common forms are excluded by `.gitignore`.
