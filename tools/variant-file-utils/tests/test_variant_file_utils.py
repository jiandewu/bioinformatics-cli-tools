import gzip
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import variant_file_utils as tool


VCF = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
1\t10\t.\tA\tG\t29\tPASS\t.
1\t20\t.\tC\tT\t31\tLowQual\t.
1\t30\t.\tG\tA\t50\tPASS\t.
1\t40\t.\tT\tC\t.\tPASS\t.
"""


class VariantFileUtilsTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.vcf = self.root / "calls.vcf"
        self.vcf.write_text(VCF)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_vcf_counts_plain_and_gzip(self):
        self.assertEqual(tool.vcf_counts(str(self.vcf)), (4, 3))
        compressed = self.root / "calls.vcf.gz"
        with gzip.open(compressed, "wt") as handle:
            handle.write(VCF)
        self.assertEqual(tool.vcf_counts(str(compressed)), (4, 3))

    def test_mean_depth(self):
        depth = self.root / "depth.tsv"
        depth.write_text("chr1\t1\t10\nchr1\t2\t20\nchr1\t3\t30\n")
        self.assertEqual(tool.mean_depth(str(depth)), 20.0)

    def test_picard_metrics(self):
        alignment = self.root / "alignment.txt"
        alignment.write_text(
            "## METRICS CLASS\n"
            "CATEGORY\tTOTAL_READS\tPF_READS_ALIGNED\tPCT_PF_READS_ALIGNED\tPF_ALIGNED_BASES\tMEAN_READ_LENGTH\tPCT_READS_ALIGNED_IN_PAIRS\n"
            "UNPAIRED\t5\t4\t0.8\t400\t100\t0\n"
            "PAIR\t100\t90\t0.9\t9000\t100\t0.88\n\n"
        )
        insert = self.root / "insert.txt"
        insert.write_text("MEDIAN_INSERT_SIZE\tMEAN_INSERT_SIZE\n250\t260.5\n")
        self.assertEqual(tool.alignment_metrics(str(alignment))["total_reads"], "100")
        self.assertEqual(tool.insert_metrics(str(insert)), {"mean_insert_size": "260.5"})

    def test_filter_vcf(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = tool.main(["filter-vcf", str(self.vcf), "--min-qual", "30", "--pass-only"])
        self.assertEqual(result, 0)
        records = [line for line in output.getvalue().splitlines() if not line.startswith("#")]
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].startswith("1\t30\t"))

    def test_integrated_json_summary(self):
        depth = self.root / "depth.tsv"
        depth.write_text("chr1\t1\t5\nchr1\t2\t15\n")
        output = io.StringIO()
        with redirect_stdout(output):
            tool.main([
                "summary", "--sample", "demo", "--vcf", f"raw={self.vcf}",
                "--depth", str(depth), "--format", "json",
            ])
        self.assertIn('"raw_variants": 4', output.getvalue())
        self.assertIn('"mean_depth": 10.0', output.getvalue())

    def test_allele_balance_windows_and_sample_selection(self):
        vcf = self.root / "multisample.vcf"
        vcf.write_text(
            "##fileformat=VCFv4.2\n"
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tcase\tcontrol\n"
            "chr1\t1\t.\tA\tG\t50\tPASS\t.\tGT:AD\t0/1:6,4\t0/0:9,1\n"
            "chr1\t100\t.\tC\tT,G\t50\tPASS\t.\tGT:AD\t1/2:5,2,3\t0/0:10,0,0\n"
            "chr1\t1001\t.\tG\tA\t50\tPASS\t.\tGT:AD\t0/1:8,2\t0/0:10,0\n"
            "chr1\t1100\t.\tT\tC\t50\tPASS\t.\tGT:DP\t0/1:10\t0/0:10\n"
        )
        rows = tool.allele_balance_rows(str(vcf), ["case"], 1000, 4, 79, 1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["start"], 1)
        self.assertEqual(rows[0]["variants"], 2)
        self.assertEqual(rows[0]["ref_depth"], 11)
        self.assertEqual(rows[0]["alt_depth"], 9)
        self.assertEqual(rows[0]["alt_fraction"], 0.45)
        self.assertEqual(rows[1]["start"], 1001)

    def test_allele_balance_cli_defaults_to_all_samples(self):
        vcf = self.root / "multisample.vcf"
        vcf.write_text(
            "##fileformat=VCFv4.2\n"
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tfirst\tsecond\n"
            "chr2\t5\t.\tA\tG\t50\tPASS\t.\tGT:AD\t0/1:5,5\t0/1:7,3\n"
        )
        output = io.StringIO()
        with redirect_stdout(output):
            tool.main(["allele-balance", str(vcf), "--min-variants", "1"])
        self.assertIn("first\tchr2", output.getvalue())
        self.assertIn("second\tchr2", output.getvalue())

if __name__ == "__main__":
    unittest.main()
