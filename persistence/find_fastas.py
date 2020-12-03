
# Find clockwork fasta files that
# - run out of one site, eg. ebi
# - run out of clockwork pipeline, in this case, names are gvcf.fasta
# - mapped to tb reference, namely:  NC_000962.3

# Then copy those fasta files in destinated folder (/work/persistence-catwalk)
# - with a new name, site_uuid + run_uuid + sampel_name__

import shutil
from pathlib import Path
import json
import sys, os, time

import argh

def find_fasta_files_for_run(site_uuid, run_uuid):
    target_folder = Path(f'/work/persistence/{site_uuid}/work/output/{run_uuid}')
    result = []
    if target_folder.is_dir():
        result = list(target_folder.glob('*/minos/gvcf.fasta'))
    return result

def is_sample_correct_ref(site_uuid, run_uuid, sample_name, sample_ref):
    try:
        p = f'/work/persistence/{site_uuid}/work/output/{run_uuid}/{sample_name}/speciation/reference_info.txt'
        with open(p) as f:
            data = json.loads(f.read())

            if data['pick_taxid'] == sample_ref:
                return True
    except Exception as e:
        print(str(e))
    return False

def get_sample_name(p):
    return p.parent.parent.name

def copy_fasta_files(site_uuid, run_uuid, sample_ref, area, existing_fasta_files):
    count = 0
    fasta_files = find_fasta_files_for_run(site_uuid, run_uuid)
    for f in fasta_files:
        sample_name = get_sample_name(f)
        run_sample_fasta_name = run_uuid + "_" + sample_name + ".fasta"
        if run_sample_fasta_name in existing_fasta_files:
            continue

        if is_sample_correct_ref(site_uuid, run_uuid, sample_name, sample_ref):
            dest = Path(f'/work/persistence-catwalk/fasta/{area}/{site_uuid}/{sample_ref}/{run_sample_fasta_name}')
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

def insert_fasta_files_to_catwalk(area, site_uuid, sample_ref):
    samples_already_there = set([x.name for x in Path("/home/ubuntu/catwalk/test").glob("*")])
    all_samples = list(Path("/work/persistence-catwalk/fasta").glob(f"{area}/*/{sample_ref}/*.fasta"))

    for sample in all_samples:
        if sample.stem not in samples_already_there:
            cmd = f"/home/ubuntu/catwalk/cw_client add_sample -f {sample}"
            print(cmd)
            os.system(cmd)
            time.sleep(0.5)

def find_all_fasta_files(area, site_uuid, sample_ref):
    return { x.name for x in Path(f"/work/persistence-catwalk/fasta/{area}/{site_uuid}/{sample_ref}").glob("*.fasta") }

def go(area = 'global-prod', site_uuid = '1fd86041-5b36-4208-8eb4-cf825d37c6a6', sample_ref = 'NC_000962.3'):
    runs = find_all_runs(site_uuid)
    print(f"number of runs found for site uuid {site_uuid}: {len(runs)}")
    existing_fasta_files = find_all_fasta_files(area, site_uuid, sample_ref)
    for run in runs:
        copy_fasta_files(site_uuid, run, sample_ref, area, existing_fasta_files)
    insert_fasta_files_to_catwalk(area, site_uuid, sample_ref)

if __name__ == '__main__':
    argh.dispatch_command(go)

