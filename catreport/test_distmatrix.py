# Test distmatrix.py

# Run all tests: python3 test_distmatrix.py

# Run with a fasta file: python3 test_distmatrix.py /work/output/eb511608-2398-4ce7-9214-39c39b770abe/SRR7800432/minos/gvcf.fasta

import sys
import unittest

import distmatrix


def main():
    if len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            content = f.read()
        max_header, max_seq, counts, headers = distmatrix.parse_fasta(content)
        print(max_header)
        print(counts)
        print(headers)


class TestDistMatrix(unittest.TestCase):
    def setUp(self):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_parse_fasta_single(self):
        input = ">Header\nACGTACGTACGT\nACGTACGTACGT\nACGTACGTACGT\nACGTACGTACGT\nACGTACGTACGT\n"
        max_header, max_seq, counts, headers = distmatrix.parse_fasta(input)
        self.assertEqual(max_header, ">Header")

        self.assertEqual(
            max_seq, "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
        )
        self.assertEqual(counts["A"], 15)
        self.assertEqual(counts["G"], 15)
        self.assertEqual(counts["C"], 15)
        self.assertEqual(counts["T"], 15)

    def test_parse_fasta_multiple(self):
        input = ">Header1\nACGTACGTACGT\nACGTACGTACGT\nACGTACGTACGT\nACGTACGTACGT\nACGTACGTACGT\n>Header2\nACGTACGTACGT\nACGTACGTACGT\nACGTACGTACGT\n"
        max_header, max_seq, counts, headers = distmatrix.parse_fasta(input)
        self.assertEqual(max_header, ">Header1")
        self.assertEqual(
            max_seq, "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
        )
        self.assertEqual(counts["A"], 15)
        self.assertEqual(counts["G"], 15)
        self.assertEqual(counts["C"], 15)
        self.assertEqual(counts["T"], 15)

    def test_distance_withN(self):
        seq1 = "ACGTNNACGT"
        seq2 = "ACGTACACGT"
        result = distmatrix.distance(seq1, seq2)
        self.assertEqual(result, 0)

    def test_distance_withoutN(self):
        seq1 = "ACGTGTACGT"
        seq2 = "ACGTACACGT"
        result = distmatrix.distance(seq1, seq2)
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
    # main()
