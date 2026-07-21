# Cell Ranger HDF5 utilities

Small R utilities for inspecting, reading, and safely merging sparse 10x Genomics Cell Ranger HDF5 count matrices.

## What is included

- `R/cellranger_h5.R`: reusable functions for reading and merging matrices.
- `scripts/inspect_h5.R`: list the groups and datasets in an HDF5 file.
- `scripts/merge_h5.R`: merge compatible matrices and save an RDS object.
- `environment.yml`: reproducible R environment.

No study data, sample metadata, manuscript files, credentials, or server-specific paths are included.

## Environment

Create and activate the Conda environment:

```bash
conda env create -f environment.yml
conda activate cellranger-hdf5-utils
```

## Inspect a file

```bash
Rscript scripts/inspect_h5.R data/sample_filtered_feature_bc_matrix.h5
```

## Merge matrices

Pass the output path first, followed by one or more Cell Ranger HDF5 files:

```bash
Rscript scripts/merge_h5.R results/merged_counts.rds \
  data/sample_a_filtered_feature_bc_matrix.h5 \
  data/sample_b_filtered_feature_bc_matrix.h5
```

The saved RDS object contains:

- `counts`: a sparse feature-by-cell matrix;
- `features`: feature IDs, names, and types;
- `samples`: input paths and cell counts;
- `summary`: matrix dimensions and sparsity.

Cell barcodes are prefixed with the input filename-derived sample ID. Merging stops if feature IDs or their order differ among files.

For programmatic use:

```r
source("R/cellranger_h5.R")

result <- merge_10x_h5(
  c("data/sample_a.h5", "data/sample_b.h5"),
  sample_ids = c("sample_a", "sample_b"),
  feature_type = "Gene Expression"
)
```

## Data policy

HDF5 inputs and generated R objects are ignored by Git. Keep controlled or unpublished study data outside this repository and review staged files before every push:

```bash
git status
git diff --cached
```
