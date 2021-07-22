#!/usr/env/python3

import unittest
import glob
import sys
import shutil
import os
import utils
import uuid
from operator import itemgetter

class TestCatweb(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # May need to change profile depending on deployment environment
        cls.profile = "-profile singularity"
        cls.sampleNames = ("aa627688-96ac-11eb-ac3f-0200170119d8","3b3ed8e6-96ac-11eb-ac3f-0200170119d8")

        cls.nextflowFile = "/data/pipelines/ncov2019-artic-nf/main.nf"
        cls.readPattern = "'*{1,2}.fastq.gz'"
        cls.obj_path = "/data/pipelines/ncov2019-artic-nf/objStoreExample.csv"
        cls.outputDir = "/work/output/test_catweb/"

        utils.syscall('rm -rf ' + cls.outputDir + '/*')

    # @classmethod
    # def tearDownClass(cls):
    #     utils.syscall('rm -rf ' + cls.outputDir + '/*')
  
    def test_ncov_illumina_viridian(self):

        # Should do through catsgo
        # e.g. cd catsgo; python3 catsgo.py run-covid-illumina-objstore oxforduni-ncov2019-artic-nf-illumina /data/pipelines/ncov2019-artic-nf/objStoreExample.csv
        #
        # Left out --pipeline_name oxforduni-ncov2019-artic-nf-illumina --run_uuid cc8ee708-942e-4214-8fb8-5ace52b8914e --head_node_ip 10.0.1.2
        command = ' '.join([
            'nextflow -q run', self.nextflowFile, self.profile,
            '-with-trace -with-report -with-timeline -with-dag dag.png',
            '--pipeline_name oxforduni-ncov2019-artic-nf-illumina', '--run_uuid', str(uuid.uuid4()) , '--head_node_ip 10.0.1.2',
            '--readpat', self.readPattern,
            '--illumina',
            '--prefix', 'illumina',
            '-process.executor', 'slurm',
            '--objstore', self.obj_path,
            '--varCaller', 'viridian',
            '--refmap', "'\"{}\"'",
            '--outdir', self.outputDir
        ])
        utils.syscall(command)
        self.assertTrue(True)

    def test_ncov_illumina_viridian_output_has_output_folder(self):
        self.assertTrue(os.path.exists(self.outputDir))

    def test_ncov_illumina_viridian_output_has_consensus_folder(self):
        qc_dir = os.path.join(self.outputDir, 'consensus_seqs')
        self.assertTrue(os.path.exists(qc_dir))
    
    def test_ncov_illumina_viridian_output_has_analysis_folder(self):
        qc_dir = os.path.join(self.outputDir, 'analysis')
        self.assertTrue(os.path.exists(qc_dir))      

    def test_ncov_illumina_viridian_output_classification_has_human_read_list_file(self):
        for sample in self.sampleNames:
            filepath = os.path.join('consensus_seqs', sample + '.fasta')
            outputFile = os.path.join(self.outputDir, filepath)
            self.assertTrue(os.path.exists(outputFile))
            expectedFile = os.path.join("tests/expectedOutput/", filepath)
            expected_md5 = utils.md5(expectedFile)
            outputFile_md5 = utils.md5(outputFile)
            self.assertEqual(expected_md5, outputFile_md5)

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCatweb)
    unittest.TextTestRunner(verbosity=2).run(suite)