import tempfile
import unittest
import zipfile
from pathlib import Path

import fastqc_summary


FASTQC_DATA = """##FastQC\t0.12.1
>>Basic Statistics\tpass
#Measure\tValue
Filename\tsample_R1.fastq.gz
File type\tConventional base calls
Encoding\tSanger / Illumina 1.9
Total Sequences\t100
Sequences flagged as poor quality\t2
Sequence length\t5
%GC\t48
>>END_MODULE
>>Per base sequence quality\twarn
#Base\tMean\tMedian\tLower Quartile\tUpper Quartile\t10th Percentile\t90th Percentile
1\t35.0\t35.0\t34.0\t36.0\t32.0\t38.0
2-3\t25.0\t25.0\t24.0\t26.0\t22.0\t28.0
4-5\t15.0\t15.0\t14.0\t16.0\t12.0\t18.0
>>END_MODULE
"""


class FastqcSummaryTests(unittest.TestCase):
    def test_parse_weighted_quality_cycles(self):
        summary = fastqc_summary.parse_fastqc(
            FASTQC_DATA.splitlines(), source="fixture"
        )
        self.assertEqual(summary.filename, "sample_R1.fastq.gz")
        self.assertEqual(summary.total_sequences, "100")
        self.assertEqual(summary.filtered_sequences, "2")
        self.assertEqual(summary.sequence_length, "5")
        self.assertEqual(summary.percent_gc, "48")
        self.assertEqual(summary.per_base_quality_status, "warn")
        self.assertEqual(summary.cycle_percent_mean_q20, "60.00")
        self.assertEqual(summary.cycle_percent_mean_q30, "20.00")

    def test_read_zip_archive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "sample_fastqc.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("sample_fastqc/fastqc_data.txt", FASTQC_DATA)
            lines = fastqc_summary.read_fastqc_lines(archive_path)
            summary = fastqc_summary.parse_fastqc(lines, source=str(archive_path))
        self.assertEqual(summary.filename, "sample_R1.fastq.gz")
        self.assertEqual(summary.cycle_percent_mean_q20, "60.00")

    def test_rejects_unknown_base_label(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            fastqc_summary._base_width("1,2")


if __name__ == "__main__":
    unittest.main()
