# Find clockwork fasta files that
# - run out of one site, eg. ebi
# - run out of clockwork pipeline, in this case, names are gvcf.fasta
# - mapped to tb reference, namely:  NC_000962.3

# Then copy those fasta files in destinated folder (/work/persistence-catwalk)
# - with a new name, site_uuid + run_uuid + sampel_name__

import shutil
from pathlib import Path
import json
import sys

def find_tb_fasta_files_for_run(site_uuid, run_uuid):
    target_folder = Path(f'/work/persistence/{site_uuid}/work/output/{run_uuid}')
    result = []
    if target_folder.is_dir():
        result = list(target_folder.glob('*/minos/gvcf.fasta'))
    return result

def tb_or_not_tb(site_uuid, run_uuid, sample_name):
    try:
        p = f'/work/persistence/{site_uuid}/work/output/{run_uuid}/{sample_name}/speciation/reference_info.txt'
        with open(p) as f:
            data = json.loads(f.read())

            if data['pick_taxid'] == 'NC_000962.3':
                return True
    except Exception as e:
        print(str(e))
    return False

def get_sample_name(p):
    return p.parent.parent.name

def copy_fasta_files(site_uuid, run_uuid):
    count = 0
    fasta_files = find_tb_fasta_files_for_run(site_uuid, run_uuid)
    for f in fasta_files:
        sample_name = get_sample_name(f)
        print(f"f={f}, sample_name={sample_name}")
        
        if tb_or_not_tb(site_uuid, run_uuid, get_sample_name(f)):
            dest = Path(f'/work/persistence-catwalk/{run_uuid}_{sample_name}.fasta')
            if not dest.exists():
                count += 1
                shutil.copyfile(f, dest)
                print(f'{f} copied to {dest}')
    print(f'Total {count} files copied.')

def find_all_runs(site_uuid):
    target_folder = Path(f'/work/persistence/{site_uuid}/work/output')
    result = []
    if target_folder.is_dir():
        result = [x.name for x in target_folder.iterdir()]
    return result
        
if __name__ == '__main__':
    site_uuid = '1fd86041-5b36-4208-8eb4-cf825d37c6a6'
    if len(sys.argv) == 2:
        site_uuid = sys.argv[1]

    runs = find_all_runs(site_uuid)
    print(runs)
    for run in runs:
        copy_fasta_files(site_uuid,run)
    
