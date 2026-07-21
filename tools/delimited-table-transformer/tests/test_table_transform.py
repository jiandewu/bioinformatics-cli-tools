from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "table_transform.py"


class TableTransformCliTests(unittest.TestCase):
    def run_cli(self, table: str, command: str, *arguments: str):
        with tempfile.TemporaryDirectory() as directory:
            table_path = Path(directory) / "table.txt"
            table_path.write_text(table, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), command, str(table_path), *arguments],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_transpose_csv_with_quoted_field(self):
        result = self.run_cli(
            'id,note\nA,"hello, world"\n', "transpose", "--delimiter", "comma"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'id,A\nnote,"hello, world"\n')

    def test_swap_columns(self):
        result = self.run_cli("a\tb\tc\n1\t2\t3\n", "swap-columns", "1", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "c\tb\ta\n3\t2\t1\n")

    def test_swap_rows(self):
        result = self.run_cli("header\nfirst\nsecond\n", "swap-rows", "2", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "header\nsecond\nfirst\n")

    def test_unique_fields_preserves_order(self):
        result = self.run_cli("a\tb\ta\tc\tb\n", "unique-fields")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "a\tb\tc\n")

    def test_match_columns_keeps_first_column(self):
        result = self.run_cli(
            "id\tcase_score\tcontrol_score\tnote\nA\t2\t3\tx\n",
            "match-columns",
            "score",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout, "id\tcase_score\tcontrol_score\nA\t2\t3\n"
        )

    def test_aggregate_by_named_key(self):
        result = self.run_cli(
            "group\tx\ty\nA\t1.5\t2\nB\t4\t5\nA\t0.5\t3\n",
            "aggregate",
            "--key-column",
            "group",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "group\tx\ty\nA\t2\t5\nB\t4\t5\n")

    def test_rejects_ragged_table(self):
        result = self.run_cli("a\tb\n1\n", "transpose")
        self.assertEqual(result.returncode, 2)
        self.assertIn("line 2 has 1 fields; expected 2", result.stderr)


if __name__ == "__main__":
    unittest.main()
