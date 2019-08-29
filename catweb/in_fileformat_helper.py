import sys
import re
import glob
import pathlib

class ENA_FilenameFormat:
    '''
    e.g.:
    ERR841824_1.fastq.gz
    ERR841824_2.fastq.gz
    '''
    def is_match(self, files):
        p = re.compile('([A-Z,0-9]+)_(?:1|2)\.fastq\.gz')
        sample_names = []
        if not files:
            return False, None
        for f in files:
            m = p.match(f)
            if not m:
                return False, None
            sample_names.append(m[1])
        return True, sample_names

    def get_pattern(self):
        return "*_{1,2}.fastq.gz"


class PHE_FilenameFormat:
    '''
    e.g.:
    ae1a3c6a-1f63-40b0-8a66-c9eba9214e8a_L001_R1_001.fastq.gz
    ae1a3c6a-1f63-40b0-8a66-c9eba9214e8a_L001_R2_001.fastq.gz
    '''
    def is_match(self, files):
        p = re.compile('(.{8}-.{4}-.{4}-.{4}-.{12})_L([0-9]{3})_R(?:1|2)_([0-9]{3})\.fastq\.gz')
        sample_names = []
        for f in files:
            m = p.match(f)
            if not m:
                return False, None
            sample_names.append(m[1])
            self.m1 = m[2]
            self.m2 = m[3]
        return True, sample_names

    def get_pattern(self):
        return f"*_L{self.m1}_R{{1,2}}_{self.m2}.fastq.gz"

class APHA_FilenameFormat:
    '''
    e.g.:
    AF-12-00335-19_S78_R1_001.fastq.gz
    AF-12-00335-19_S78_R2_001.fastq.gz
    '''
    def is_match(self, files):
        p = re.compile('(AF-[0-9][0-9]-[0-9]*-[0-9][0-9])_(.*)_R(?:1|2)_(.*)\.fastq.gz')
        sample_names = []
        for f in files:
            m = p.match(f)
            if not m:
                return False, None
            self.m1 = m[2]
            self.m2 = m[3]
            sample_names.append(m[1])
        return True, sample_names

    def get_pattern(self):
        return f"*_R{{1,2}}_{self.m2}.fastq.gz"

formats = [ENA_FilenameFormat(),
           PHE_FilenameFormat(),
           APHA_FilenameFormat()]

def guess_format(files):
    if not files:
        return ""

    for f in formats:

        is_match, sample_names = f.is_match(files)
        if is_match:
            sample_names = sorted(set(sample_names)) # unique and sorted
            return f.get_pattern(), sample_names

    return None, None

def guess_from_dir(pat):
    files = pathlib.Path(pat).glob('*')
    files = [str(x.name) for x in files]
    return guess_format(files)

def main():
    d = sys.argv[1]
    print(guess_from_dir(d))

if __name__ == '__main__':
    main()
