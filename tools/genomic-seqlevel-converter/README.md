# Genomic seqlevel converter

A small command-line R utility for converting chromosome and sequence names in genomic annotation files between conventions such as Ensembl, UCSC, and NCBI.

For example, Ensembl-style chromosome `1` can be mapped to UCSC-style `chr1` when a mapping is available.

## Why this repository exists

The original script changed a TxDb to UCSC style and then immediately changed it back to Ensembl before export. This public version makes the target style an explicit command-line argument and never overwrites the input file.

The conversion uses Bioconductor's `GenomeInfoDb::seqlevelsStyle()`. Import and export are handled by `rtracklayer`, preserving the annotation as a genomic ranges object instead of rebuilding it as a transcript database.

## Environment

```bash
conda env create -f environment.yml
conda activate genomic-seqlevel-converter
```

## Usage

```bash
Rscript scripts/convert_seqlevels.R INPUT OUTPUT STYLE
```

Convert a GFF3 annotation to UCSC sequence names:

```bash
Rscript scripts/convert_seqlevels.R \
  data/gencode.annotation.gff3 \
  results/gencode.ucsc.gff3 \
  UCSC
```

Convert it back to Ensembl style:

```bash
Rscript scripts/convert_seqlevels.R \
  results/gencode.ucsc.gff3 \
  results/gencode.ensembl.gff3 \
  Ensembl
```

The input format is inferred by `rtracklayer` from the filename or connection. GFF/GFF3, GTF, BED, and other supported formats can be used.

## Important limitations

- Only sequence names with a recognized mapping are converted.
- A naming-style conversion does not perform a genome-build lift-over.
- Inspect noncanonical contigs and scaffolds after conversion.
- Existing output files are never overwritten.

## Data policy

Annotation inputs and generated outputs are ignored by Git. Manuscripts, drafts, credentials, and local environment files are also excluded.
