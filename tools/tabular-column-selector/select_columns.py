#!/usr/bin/env python3
"""Select or remove delimited-table columns by header name."""

from __future__ import annotations

import argparse
import csv
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import TextIO


def delimiter_value(value: str) -> str:
    aliases = {"tab": "\t", "comma": ",", "semicolon": ";", "pipe": "|"}
    delimiter = aliases.get(value.lower(), value)
    if len(delimiter) != 1:
        raise argparse.ArgumentTypeError(
            "delimiter must be tab, comma, semicolon, pipe, or one character"
        )
    return delimiter


def read_names(path: Path) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8-sig") as handle:
        for raw_line in handle:
            name = raw_line.rstrip("\r\n")
            if not name or name.startswith("#") or name in seen:
                continue
            names.append(name)
            seen.add(name)
    if not names:
        raise ValueError(f"no column names found in {path}")
    return names


def input_context(path: str):
    if path == "-":
        return nullcontext(sys.stdin)
    return Path(path).open(encoding="utf-8-sig", newline="")


def select_columns(
    source: TextIO,
    destination: TextIO,
    requested: list[str],
    delimiter: str,
    exclude: bool,
    allow_missing: bool,
) -> None:
    reader = csv.reader(source, delimiter=delimiter)
    writer = csv.writer(destination, delimiter=delimiter, lineterminator="\n")

    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("input table is empty") from exc

    requested_set = set(requested)
    missing = [name for name in requested if name not in header]
    if missing and not allow_missing:
        raise ValueError("columns not found: " + ", ".join(missing))

    indices = [
        index
        for index, name in enumerate(header)
        if (name not in requested_set if exclude else name in requested_set)
    ]
    if not indices:
        raise ValueError("selection produced no columns")

    writer.writerow(header[index] for index in indices)
    expected_width = len(header)
    for line_number, row in enumerate(reader, start=2):
        if len(row) != expected_width:
            raise ValueError(
                f"line {line_number} has {len(row)} fields; expected {expected_width}"
            )
        writer.writerow(row[index] for index in indices)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select or remove delimited-table columns by exact header name."
    )
    parser.add_argument("names", type=Path, help="one column name per line")
    parser.add_argument("table", help="input table, or - for standard input")
    parser.add_argument(
        "-d",
        "--delimiter",
        default="\t",
        type=delimiter_value,
        help="tab (default), comma, semicolon, pipe, or one character",
    )
    parser.add_argument(
        "-x", "--exclude", action="store_true", help="remove listed columns"
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="ignore names that are absent from the header",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        names = read_names(args.names)
        with input_context(args.table) as source:
            select_columns(
                source,
                sys.stdout,
                names,
                args.delimiter,
                args.exclude,
                args.allow_missing,
            )
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
