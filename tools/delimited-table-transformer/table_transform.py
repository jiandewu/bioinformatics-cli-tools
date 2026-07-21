#!/usr/bin/env python3
"""Safe transformations for delimited text tables."""

from __future__ import annotations

import argparse
import csv
import sys
from contextlib import nullcontext
from decimal import Decimal, InvalidOperation
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


def input_context(path: str):
    if path == "-":
        return nullcontext(sys.stdin)
    return Path(path).open(encoding="utf-8-sig", newline="")


def read_rows(source: TextIO, delimiter: str) -> list[list[str]]:
    rows = list(csv.reader(source, delimiter=delimiter))
    if not rows:
        raise ValueError("input table is empty")
    return rows


def require_rectangular(rows: list[list[str]]) -> None:
    expected = len(rows[0])
    for line_number, row in enumerate(rows, start=1):
        if len(row) != expected:
            raise ValueError(
                f"line {line_number} has {len(row)} fields; expected {expected}"
            )


def output_writer(delimiter: str) -> csv.writer:
    return csv.writer(sys.stdout, delimiter=delimiter, lineterminator="\n")


def resolve_position(value: str, maximum: int, label: str) -> int:
    try:
        position = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a 1-based integer") from exc
    if position < 1 or position > maximum:
        raise ValueError(f"{label} must be between 1 and {maximum}")
    return position - 1


def resolve_header(header: list[str], value: str) -> int:
    if value.isdigit():
        return resolve_position(value, len(header), "key column")
    matches = [index for index, name in enumerate(header) if name == value]
    if not matches:
        raise ValueError(f"key column not found: {value}")
    if len(matches) > 1:
        raise ValueError(f"key column is duplicated: {value}")
    return matches[0]


def transform(args: argparse.Namespace) -> None:
    with input_context(args.input) as source:
        rows = read_rows(source, args.delimiter)
    writer = output_writer(args.output_delimiter or args.delimiter)

    if args.command == "transpose":
        require_rectangular(rows)
        writer.writerows(zip(*rows))
        return

    if args.command == "swap-columns":
        maximum = len(rows[0])
        first = resolve_position(args.first, maximum, "first column")
        second = resolve_position(args.second, maximum, "second column")
        require_rectangular(rows)
        for row in rows:
            row[first], row[second] = row[second], row[first]
        writer.writerows(rows)
        return

    if args.command == "swap-rows":
        first = resolve_position(args.first, len(rows), "first row")
        second = resolve_position(args.second, len(rows), "second row")
        rows[first], rows[second] = rows[second], rows[first]
        writer.writerows(rows)
        return

    if args.command == "unique-fields":
        for row in rows:
            writer.writerow(dict.fromkeys(row))
        return

    if args.command == "match-columns":
        require_rectangular(rows)
        header = rows[0]
        pattern = args.pattern.casefold() if args.ignore_case else args.pattern
        indices = [0]
        for index, name in enumerate(header[1:], start=1):
            candidate = name.casefold() if args.ignore_case else name
            if pattern in candidate:
                indices.append(index)
        if len(indices) == 1 and pattern not in (
            header[0].casefold() if args.ignore_case else header[0]
        ):
            raise ValueError(f"no header contains pattern: {args.pattern}")
        writer.writerows([row[index] for index in indices] for row in rows)
        return

    if args.command == "aggregate":
        require_rectangular(rows)
        header = rows[0]
        key_index = resolve_header(header, args.key_column)
        value_indices = [index for index in range(len(header)) if index != key_index]
        totals: dict[str, list[Decimal]] = {}
        for line_number, row in enumerate(rows[1:], start=2):
            key = row[key_index]
            if key not in totals:
                totals[key] = [Decimal(0) for _ in value_indices]
            for output_index, input_index in enumerate(value_indices):
                try:
                    totals[key][output_index] += Decimal(row[input_index])
                except InvalidOperation as exc:
                    raise ValueError(
                        f"line {line_number}, column {input_index + 1} is not numeric"
                    ) from exc
        writer.writerow(header)
        for key, sums in totals.items():
            values = iter(format(value.normalize(), "f") for value in sums)
            writer.writerow(
                key if index == key_index else next(values)
                for index in range(len(header))
            )
        return

    raise ValueError(f"unsupported command: {args.command}")


def add_table_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", help="input table, or - for standard input")
    parser.add_argument(
        "-d",
        "--delimiter",
        default="\t",
        type=delimiter_value,
        help="tab (default), comma, semicolon, pipe, or one character",
    )
    parser.add_argument(
        "--output-delimiter",
        type=delimiter_value,
        help="output delimiter; defaults to the input delimiter",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transform delimited text tables with strict validation."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    transpose = commands.add_parser("transpose", help="exchange rows and columns")
    add_table_arguments(transpose)

    swap_columns = commands.add_parser("swap-columns", help="swap two columns")
    add_table_arguments(swap_columns)
    swap_columns.add_argument("first", help="first 1-based column number")
    swap_columns.add_argument("second", help="second 1-based column number")

    swap_rows = commands.add_parser("swap-rows", help="swap two rows")
    add_table_arguments(swap_rows)
    swap_rows.add_argument("first", help="first 1-based row number")
    swap_rows.add_argument("second", help="second 1-based row number")

    unique = commands.add_parser(
        "unique-fields", help="remove repeated fields within each row"
    )
    add_table_arguments(unique)

    match = commands.add_parser(
        "match-columns", help="keep the first column and matching headers"
    )
    add_table_arguments(match)
    match.add_argument("pattern", help="literal substring to find in headers")
    match.add_argument("--ignore-case", action="store_true")

    aggregate = commands.add_parser(
        "aggregate", help="sum numeric columns for repeated keys"
    )
    add_table_arguments(aggregate)
    aggregate.add_argument(
        "--key-column",
        default="1",
        help="exact header or 1-based position [1]",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        transform(args)
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
