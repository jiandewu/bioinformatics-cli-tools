#!/usr/bin/env python3
"""Small, dependency-free utilities for VCF and sequencing QC files."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
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
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
