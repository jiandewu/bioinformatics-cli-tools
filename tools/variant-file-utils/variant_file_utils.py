#!/usr/bin/env python3
"""Small, dependency-free utilities for VCF and sequencing QC files."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
from typing import Iterable, TextIO


def open_text(path: str) -> TextIO:
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def vcf_counts(path: str) -> tuple[int, int]:
    total = passed = 0
    with open_text(path) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 8:
                raise ValueError(f"{path}:{line_number}: expected at least 8 VCF columns")
            total += 1
            if fields[6] == "PASS":
                passed += 1
    return total, passed


def mean_depth(path: str) -> float | None:
    total = 0.0
    count = 0
    with open_text(path) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) < 3:
                raise ValueError(f"{path}:{line_number}: expected CHROM POS DEPTH")
            try:
                total += float(fields[2])
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: invalid depth {fields[2]!r}") from error
            count += 1
    return total / count if count else None


def read_picard_table(path: str, required: set[str], preferred_category: str | None = None) -> dict[str, str]:
    with open_text(path) as handle:
        lines = [line.rstrip("\n") for line in handle]

    for index, line in enumerate(lines):
        header = line.split("\t")
        if not required.issubset(header):
            continue
        rows: list[dict[str, str]] = []
        for data_line in lines[index + 1 :]:
            if not data_line.strip() or data_line.startswith("#"):
                if rows:
                    break
                continue
            values = data_line.split("\t")
            if len(values) < len(header):
                break
            rows.append(dict(zip(header, values)))
        if not rows:
            raise ValueError(f"{path}: Picard metrics header has no data row")
        if preferred_category and "CATEGORY" in header:
            return next((row for row in rows if row["CATEGORY"] == preferred_category), rows[0])
        return rows[0]
    columns = ", ".join(sorted(required))
    raise ValueError(f"{path}: could not find Picard metrics columns: {columns}")


def alignment_metrics(path: str) -> dict[str, str]:
    required = {"TOTAL_READS", "PF_READS_ALIGNED", "PCT_PF_READS_ALIGNED", "PF_ALIGNED_BASES"}
    row = read_picard_table(path, required, preferred_category="PAIR")
    wanted = [
        "TOTAL_READS",
        "PF_READS_ALIGNED",
        "PCT_PF_READS_ALIGNED",
        "PF_ALIGNED_BASES",
        "MEAN_READ_LENGTH",
        "PCT_READS_ALIGNED_IN_PAIRS",
    ]
    return {name.lower(): row[name] for name in wanted if name in row}


def insert_metrics(path: str) -> dict[str, str]:
    row = read_picard_table(path, {"MEAN_INSERT_SIZE"})
    return {"mean_insert_size": row["MEAN_INSERT_SIZE"]}


def parse_labeled_path(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=PATH")
    label, path = value.split("=", 1)
    if not label or not path:
        raise argparse.ArgumentTypeError("expected non-empty LABEL=PATH")
    normalized = "".join(char if char.isalnum() else "_" for char in label.strip()).strip("_").lower()
    if not normalized:
        raise argparse.ArgumentTypeError("label must contain a letter or number")
    return normalized, path


def write_record(record: dict[str, object], output: TextIO, output_format: str) -> None:
    if output_format == "json":
        json.dump(record, output, indent=2)
        output.write("\n")
        return
    writer = csv.DictWriter(output, fieldnames=list(record), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow({key: "" if value is None else value for key, value in record.items()})


def command_summary(args: argparse.Namespace) -> None:
    record: dict[str, object] = {"sample": args.sample}
    seen: set[str] = set()
    for label, path in args.vcf:
        if label in seen:
            raise ValueError(f"duplicate VCF label: {label}")
        seen.add(label)
        total, passed = vcf_counts(path)
        record[f"{label}_variants"] = total
        record[f"{label}_pass_variants"] = passed
    if args.depth:
        record["mean_depth"] = mean_depth(args.depth)
    if args.alignment_metrics:
        record.update(alignment_metrics(args.alignment_metrics))
    if args.insert_metrics:
        record.update(insert_metrics(args.insert_metrics))

    context = open(args.output, "w", encoding="utf-8", newline="") if args.output != "-" else nullcontext(sys.stdout)
    with context as output:
        write_record(record, output, args.format)


def command_filter(args: argparse.Namespace) -> None:
    output_context = open(args.output, "w", encoding="utf-8") if args.output != "-" else nullcontext(sys.stdout)
    with open_text(args.input) as input_handle, output_context as output_handle:
        for line_number, line in enumerate(input_handle, 1):
            if line.startswith("#") or not line.strip():
                output_handle.write(line)
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 8:
                raise ValueError(f"{args.input}:{line_number}: expected at least 8 VCF columns")
            if args.pass_only and fields[6] != "PASS":
                continue
            if args.min_qual is not None:
                if fields[5] == ".":
                    continue
                try:
                    quality = float(fields[5])
                except ValueError as error:
                    raise ValueError(f"{args.input}:{line_number}: invalid QUAL {fields[5]!r}") from error
                if quality < args.min_qual:
                    continue
            output_handle.write(line)


def parse_sample_depth(format_value: str, sample_value: str, path: str, line_number: int) -> tuple[int, int] | None:
    keys = format_value.split(":")
    if "AD" not in keys:
        return None
    values = sample_value.split(":")
    ad_index = keys.index("AD")
    if ad_index >= len(values) or values[ad_index] in ("", "."):
        return None
    depths = values[ad_index].split(",")
    if len(depths) < 2 or any(value == "." for value in depths):
        return None
    try:
        numeric_depths = [int(value) for value in depths]
    except ValueError as error:
        raise ValueError(f"{path}:{line_number}: invalid AD value {values[ad_index]!r}") from error
    if any(value < 0 for value in numeric_depths):
        raise ValueError(f"{path}:{line_number}: AD depths cannot be negative")
    return numeric_depths[0], sum(numeric_depths[1:])


def allele_balance_rows(
    path: str,
    selected_samples: list[str],
    window_size: int,
    min_depth_value: int,
    max_depth_value: int | None,
    min_variants: int,
) -> list[dict[str, object]]:
    sample_names: list[str] | None = None
    sample_indices: list[int] = []
    aggregates: dict[tuple[str, str, int], list[int]] = defaultdict(lambda: [0, 0, 0])

    with open_text(path) as handle:
        for line_number, line in enumerate(handle, 1):
            if line.startswith("##") or not line.strip():
                continue
            if line.startswith("#CHROM"):
                header = line.rstrip("\n").split("\t")
                sample_names = header[9:]
                if not sample_names:
                    raise ValueError(f"{path}:{line_number}: VCF has no sample columns")
                requested = selected_samples or sample_names
                missing = [sample for sample in requested if sample not in sample_names]
                if missing:
                    raise ValueError(f"{path}: sample(s) not found: {', '.join(missing)}")
                sample_indices = [sample_names.index(sample) for sample in requested]
                selected_samples = requested
                continue
            if line.startswith("#"):
                continue
            if sample_names is None:
                raise ValueError(f"{path}:{line_number}: missing #CHROM header")
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 9 + len(sample_names):
                raise ValueError(f"{path}:{line_number}: sample columns do not match the VCF header")
            try:
                position = int(fields[1])
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: invalid POS {fields[1]!r}") from error
            if position < 1:
                raise ValueError(f"{path}:{line_number}: POS must be positive")
            window_index = (position - 1) // window_size
            for sample, sample_index in zip(selected_samples, sample_indices):
                depths = parse_sample_depth(fields[8], fields[9 + sample_index], path, line_number)
                if depths is None:
                    continue
                ref_depth, alt_depth = depths
                total_depth = ref_depth + alt_depth
                if total_depth < min_depth_value:
                    continue
                if max_depth_value is not None and total_depth > max_depth_value:
                    continue
                values = aggregates[(sample, fields[0], window_index)]
                values[0] += 1
                values[1] += ref_depth
                values[2] += alt_depth

    if sample_names is None:
        raise ValueError(f"{path}: missing #CHROM header")

    rows: list[dict[str, object]] = []
    for (sample, chromosome, window_index), (variant_count, ref_depth, alt_depth) in aggregates.items():
        if variant_count < min_variants:
            continue
        total = ref_depth + alt_depth
        rows.append({
            "sample": sample,
            "chromosome": chromosome,
            "start": window_index * window_size + 1,
            "end": (window_index + 1) * window_size,
            "variants": variant_count,
            "ref_depth": ref_depth,
            "alt_depth": alt_depth,
            "alt_fraction": alt_depth / total if total else None,
            "alt_ref_ratio": alt_depth / ref_depth if ref_depth else math.inf,
        })
    return rows


def command_allele_balance(args: argparse.Namespace) -> None:
    rows = allele_balance_rows(
        args.input,
        args.sample,
        args.window_size,
        args.min_depth,
        args.max_depth,
        args.min_variants,
    )
    output_context = open(args.output, "w", encoding="utf-8", newline="") if args.output != "-" else nullcontext(sys.stdout)
    fieldnames = [
        "sample", "chromosome", "start", "end", "variants", "ref_depth",
        "alt_depth", "alt_fraction", "alt_ref_ratio",
    ]
    with output_context as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary = subparsers.add_parser("summary", help="combine VCF, depth, and Picard metrics")
    summary.add_argument("--sample", required=True, help="sample identifier for the output row")
    summary.add_argument("--vcf", action="append", default=[], type=parse_labeled_path, metavar="LABEL=PATH")
    summary.add_argument("--depth", help="samtools depth-style CHROM POS DEPTH file")
    summary.add_argument("--alignment-metrics", help="Picard alignment summary metrics file")
    summary.add_argument("--insert-metrics", help="Picard insert size metrics file")
    summary.add_argument("--format", choices=("tsv", "json"), default="tsv")
    summary.add_argument("--output", default="-", help="output path (default: stdout)")
    summary.set_defaults(func=command_summary)

    filtering = subparsers.add_parser("filter-vcf", help="filter VCF records without changing headers")
    filtering.add_argument("input", help="input .vcf or .vcf.gz")
    filtering.add_argument("--min-qual", type=float, help="keep records with QUAL at least this value")
    filtering.add_argument("--pass-only", action="store_true", help="keep only records whose FILTER is PASS")
    filtering.add_argument("--output", default="-", help="output VCF path (default: stdout)")
    filtering.set_defaults(func=command_filter)

    balance = subparsers.add_parser(
        "allele-balance", help="aggregate FORMAT/AD allele depths in genomic windows"
    )
    balance.add_argument("input", help="input multisample .vcf or .vcf.gz")
    balance.add_argument("--sample", action="append", default=[], help="sample name (repeatable; default: all)")
    balance.add_argument("--window-size", type=int, default=1_000_000, help="window size in bases (default: 1000000)")
    balance.add_argument("--min-depth", type=int, default=4, help="minimum ref+alt depth (default: 4)")
    balance.add_argument("--max-depth", type=int, default=79, help="maximum ref+alt depth (default: 79)")
    balance.add_argument("--min-variants", type=int, default=10, help="minimum variants per output window (default: 10)")
    balance.add_argument("--output", default="-", help="output TSV path (default: stdout)")
    balance.set_defaults(func=command_allele_balance)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        for name in ("window_size", "min_depth", "max_depth", "min_variants"):
            if hasattr(args, name) and getattr(args, name) is not None and getattr(args, name) < 1:
                raise ValueError(f"--{name.replace('_', '-')} must be at least 1")
        if hasattr(args, "max_depth") and args.max_depth is not None and args.max_depth < args.min_depth:
            raise ValueError("--max-depth must be greater than or equal to --min-depth")
        args.func(args)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
