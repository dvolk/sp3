import sys
import argparse
import pathlib
import sqlite3
import json
import collections

def perform_analysis(samples):
    drug_predictions = collections.defaultdict(list)
    genes = collections.defaultdict(int)
    mutations = collections.defaultdict(int)

    for sample_name, sample_json in samples.items():
        if sample_json['status'] != 'success':
            continue

        if 'data' not in sample_json:
            continue

        for drug, prediction in sample_json['data']['metadata'].items():
            drug_predictions[drug].append(prediction)

        for effect in sample_json['data']['effects']:
            genes[effect['gene_name']] += 1
            mutations[effect['mutation_name']] += 1

    print('1. metadata')
    for drug, predictions in drug_predictions.items():
        print(drug, collections.Counter(predictions))

    genes = sorted(genes.items(), key = lambda item: item[1], reverse=True)
    genes = { k:v for k,v in genes }
    mutations = sorted(mutations.items(), key = lambda item: item[1], reverse=True)
    mutations = { k:v for k,v in mutations }

    print('2. effects')
    print('2.1 genes')
    for gene_name, count in genes.items():
        print('gene:', gene_name, 'count:', count)
    print('2.2 mutations')
    for mutation_name, count in mutations.items():
        print('mutation:', mutation_name, 'count:', count)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pipeline_run_uuid', required=True)
    parser.add_argument('--catreport_db_path', required=True)
    args = parser.parse_args()

    # get catreport database
    con = sqlite3.connect(args.catreport_db_path)
    con.row_factory = sqlite3.Row
    res_rows = con.execute("select * from q where pipeline_run_uuid = ? and type = ?",
                           (args.pipeline_run_uuid, "resistance"))

    # create dictionary from sample_name to report json
    sample_json = dict()
    for row in res_rows:
        sample_name = row['sample_name']
        with open(row['report_filename']) as f:
            sample_json[sample_name] = json.loads(f.read())

    perform_analysis(sample_json)

if __name__ == "__main__":
    main()
