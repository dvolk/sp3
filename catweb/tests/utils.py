import hashlib
import subprocess
import datetime
import os
import sys
import gzip

class Error (Exception): pass

def syscall(command):
    completed_process = subprocess.run(command, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, universal_newlines=True)
    if completed_process.returncode != 0:
        print('Error running this command:', command, file=sys.stderr)
        print('Return code:', completed_process.returncode, file=sys.stderr)
        print('Output from stdout and stderr:', completed_process.stdout, sep='\n', file=sys.stderr)
        raise Error('Error in system call. Cannot continue')

    return completed_process


def md5(filename):
    '''Given a file, returns a string that is the md5 sum of the file'''
    # see https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def md5_from_gzip(filename):
    '''Given a gzip file, returns a string that is the md5 sum of the file'''
    # see https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    hash_md5 = hashlib.md5()
    with gzip.open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_md5_from_file(filename):
    '''Loads md5 from file, where could have been made my 'md5' on a mac,
    or 'md5sum' in linux. Assumes just one md5 in the file - only looks at
    the first line'''
    with open(filename) as f:
        line = f.readline().rstrip()

    # Mac:
    # MD5 (filename) = md5
    # Linux:
    # md5  filename
    try:
        if line.startswith('MD5'):
            md5sum = line.split()[-1]
        else:
            md5sum = line.split()[0]
    except:
        raise Error('Error getting md5 from file ' + filename + '. Unexpected format')

    if len(md5sum) != 32:
        raise Error('Error getting md5 from file ' + filename + '. Expected string of length 32')

    return md5sum
