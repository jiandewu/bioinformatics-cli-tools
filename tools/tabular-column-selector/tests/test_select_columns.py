from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "select_columns.py"


class SelectColumnsCliTests(unittest.TestCase):
    def run_cli(self, names: str, table: str, *options: str):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            names_path = base / "names.txt"
            table_path = base / "table.tsv"
            names_path.write_text(names, encoding="utf-8")
            table_path.write_text(table, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), *options, str(names_path), str(table_path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_selects_in_input_order_and_handles_quoted_fields(self):
        result = self.run_cli(
            "score\nid\n", 'id\tnote\tscore\nA1\t"alpha\tbeta"\t8\n'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "id\tscore\nA1\t8\n")

    def test_excludes_columns(self):
        result = self.run_cli("note\n", "id\tnote\tscore\nA1\tok\t8\n", "--exclude")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "id\tscore\nA1\t8\n")

    def test_reports_missing_columns(self):
        result = self.run_cli("unknown\n", "id\tscore\nA1\t8\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("columns not found: unknown", result.stderr)

    def test_supports_csv(self):
        result = self.run_cli(
            "note\n", 'id,note\nA1,"hello, world"\n', "--delimiter", "comma"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            list(csv.reader(result.stdout.splitlines())),
            [["note"], ["hello, world"]],
        )


if __name__ == "__main__":
    unittest.main()
