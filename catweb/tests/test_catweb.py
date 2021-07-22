#!/usr/env/python3

import unittest
import glob
import sys
import shutil
import os
import utils
import uuid
import subprocess
import yaml
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
        # e.g. cd ~/catsgo; python3 catsgo.py run-covid-illumina-objstore oxforduni-ncov2019-artic-nf-illumina /data/pipelines/ncov2019-artic-nf/objStoreExample.csv
        # command = ' '.join([
        #     'nextflow -q run', self.nextflowFile, self.profile,
        #     '-with-trace -with-report -with-timeline -with-dag dag.png',
        #     '--pipeline_name oxforduni-ncov2019-artic-nf-illumina', '--run_uuid', str(uuid.uuid4()) , '--head_node_ip 10.0.1.2',
        #     '--readpat', self.readPattern,
        #     '--illumina',
        #     '--prefix', 'illumina',
        #     '-process.executor', 'slurm',
        #     '--objstore', self.obj_path,
        #     '--varCaller', 'viridian',
        #     '--refmap', "'\"{}\"'",
        #     '--outdir', self.outputDir
        # ])
        command = 'python3 catsgo.py run-covid-illumina-objstore oxforduni-ncov2019-artic-nf-illumina /data/pipelines/ncov2019-artic-nf/objStoreExample.csv'
        completed_process = subprocess.run(command, cwd='/home/ubuntu/catsgo', shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, universal_newlines=True)
        if completed_process.returncode != 0:
            print('Error running this command:', command, file=sys.stderr)
            print('Return code:', completed_process.returncode, file=sys.stderr)
            print('Output from stdout and stderr:', completed_process.stdout, sep='\n', file=sys.stderr)
            raise utils.Error('Error in system call. Cannot continue')
        
        print(f"ran command {command}")
        run_uuid = yaml.load(completed_process.stdout, Loader=yaml.SafeLoader)['run_uuid']
        print(f"run uuid {run_uuid}")
        complete = False
        checkCommand = f"python3 catsgo.py check-run oxforduni-ncov2019-artic-nf-illumina {run_uuid}"
        while not complete:
            completed_check = subprocess.run(checkCommand, cwd='/home/ubuntu/catsgo', shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, universal_newlines=True)
            if completed_check.returncode != 0:
                print('Error running this command:', command, file=sys.stderr)
                print('Return code:', completed_check.returncode, file=sys.stderr)
                print('Output from stdout and stderr:', completed_check.stdout, sep='\n', file=sys.stderr)
                raise utils.Error('Error in system call. Cannot continue')
            print(f"ran command {checkCommand}")
            print(f"output: {completed_check.stdout}")

            if (completed_check.stdout.strip() == "OK"):
                complete = True
            elif not (completed_check.stdout.strip() == "Running"):
                print('Unexpected Run Status')
                print('Output from stdout and stderr:', completed_check.stdout, sep='\n', file=sys.stderr)
                raise utils.Error('Error in catsgo run. Cannot continue')
                
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