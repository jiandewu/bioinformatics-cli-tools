#!/usr/bin/env python3
"""Create a tabular summary from FastQC text reports or ZIP archives."""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, TextIO

MODULE_START = re.compile(r"^>>([^\t]+)\t([^\t]+)")
BASE_RANGE = re.compile(r"^(\d+)(?:-(\d+))?$")


@dataclass
class FastqcSummary:
    source: str
    filename: str = "NA"
    total_sequences: str = "NA"
    filtered_sequences: str = "NA"
    sequence_length: str = "NA"
    percent_gc: str = "NA"
    per_base_quality_status: str = "NA"
    cycle_percent_mean_q20: str = "NA"
    cycle_percent_mean_q30: str = "NA"


def _find_fastqc_member(archive: zipfile.ZipFile) -> str:
    members = [
        name
        for name in archive.namelist()
        if name == "fastqc_data.txt" or name.endswith("/fastqc_data.txt")
    ]
    if len(members) != 1:
        raise ValueError(
            f"Expected one fastqc_data.txt in archive, found {len(members)}"
        )
    return members[0]


def read_fastqc_lines(path: Path) -> list[str]:
    """Read FastQC text output from a ZIP archive, directory, or text file."""
    if path.is_dir():
        candidates = sorted(path.rglob("fastqc_data.txt"))
        if len(candidates) != 1:
            raise ValueError(
                f"Expected one fastqc_data.txt under {path}, found {len(candidates)}"
            )
        return candidates[0].read_text(encoding="utf-8").splitlines()

    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            member = _find_fastqc_member(archive)
            with archive.open(member) as handle:
                return io.TextIOWrapper(handle, encoding="utf-8").read().splitlines()

    return path.read_text(encoding="utf-8").splitlines()


def _base_width(label: str) -> int:
    match = BASE_RANGE.fullmatch(label)
    if not match:
        raise ValueError(f"Unsupported FastQC base-position label: {label}")
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if end < start:
        raise ValueError(f"Invalid FastQC base-position range: {label}")
    return end - start + 1


def parse_fastqc(lines: Iterable[str], source: str) -> FastqcSummary:
    """Parse selected Basic Statistics and Per base sequence quality fields."""
    summary = FastqcSummary(source=source)
    current_module: str | None = None
    quality_positions = 0
    mean_q20_positions = 0
    mean_q30_positions = 0

    for line in lines:
        module_match = MODULE_START.match(line)
        if module_match:
            current_module = module_match.group(1)
            if current_module == "Per base sequence quality":
                summary.per_base_quality_status = module_match.group(2)
            continue

        if line == ">>END_MODULE":
            current_module = None
            continue
        if not line or line.startswith("#"):
            continue

        fields = line.split("\t")
        if current_module == "Basic Statistics" and len(fields) >= 2:
            key, value = fields[0], fields[1]
            field_map = {
                "Filename": "filename",
                "Total Sequences": "total_sequences",
                "Sequences flagged as poor quality": "filtered_sequences",
                "Sequence length": "sequence_length",
                "%GC": "percent_gc",
            }
            if key in field_map:
                setattr(summary, field_map[key], value)

        elif current_module == "Per base sequence quality" and len(fields) >= 2:
            width = _base_width(fields[0])
            mean_quality = float(fields[1])
            quality_positions += width
            if mean_quality >= 20:
                mean_q20_positions += width
            if mean_quality >= 30:
                mean_q30_positions += width

    if quality_positions:
        summary.cycle_percent_mean_q20 = (
            f"{100 * mean_q20_positions / quality_positions:.2f}"
        )
        summary.cycle_percent_mean_q30 = (
            f"{100 * mean_q30_positions / quality_positions:.2f}"
        )
    return summary


def write_summaries(summaries: Iterable[FastqcSummary], output: TextIO) -> None:
    fieldnames = list(FastqcSummary.__dataclass_fields__)
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    for summary in summaries:
        writer.writerow(asdict(summary))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize FastQC ZIP archives or fastqc_data.txt reports."
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output TSV path; defaults to standard output."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summaries = []
    for path in args.inputs:
        if not path.exists():
            raise FileNotFoundError(f"Input does not exist: {path}")
        summaries.append(parse_fastqc(read_fastqc_lines(path), str(path)))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            write_summaries(summaries, handle)
    else:
        write_summaries(summaries, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
