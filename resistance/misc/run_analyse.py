"""
Given a pipeline run uuid and a catreport database path, get drug resistance
gene, and mutation counts by parsing the piezo resistance report
"""

import argparse
import collections
import json
import pathlib
import sqlite3
import sys


def perform_analysis(samples):
    drug_predictions = collections.defaultdict(list)
    genes = collections.defaultdict(int)
    mutations = collections.defaultdict(int)
    gene_muts = collections.defaultdict(int)

    for sample_name, sample_json in samples.items():
        if sample_json["status"] != "success":
            continue

        if "data" not in sample_json:
            continue

        for drug, prediction in sample_json["data"]["metadata"].items():
            drug_predictions[drug].append(prediction)

        for effect in sample_json["data"]["effects"]:
            genes[effect["gene_name"]] += 1
            mutations[effect["mutation_name"]] += 1
            full_name = effect["gene_name"] + "_" + effect["mutation_name"]
            gene_muts[full_name] += 1

    print("1. metadata")

    for drug, predictions in drug_predictions.items():
        print(drug, collections.Counter(predictions))

    genes = sorted(genes.items(), key=lambda item: item[1], reverse=True)
    genes = {k: v for k, v in genes}
    mutations = sorted(mutations.items(), key=lambda item: item[1], reverse=True)
    mutations = {k: v for k, v in mutations}
    gene_muts = sorted(gene_muts.items(), key=lambda item: item[1], reverse=True)
    gene_muts = {k: v for k, v in gene_muts}

    print("2. effects")

    print("2.1 genes")
    for gene_name, count in genes.items():
        print("gene:", gene_name, "count:", count)

    print("2.2 mutations")
    for mutation_name, count in mutations.items():
        print("mutation:", mutation_name, "count:", count)

    print("2.3 gene + mutations")
    for gene_mut, count in gene_muts.items():
        print("mutation:", gene_mut, "count:", count)

    return {
        "drug_predictions": drug_predictions,
        "genes": genes,
        "mutations": mutations,
        "gene_muts": gene_muts,
    }


def save_analysis(d, pipeline_run_uuid):
    with open(f"{pipeline_run_uuid}.res.json", "w") as f:
        f.write(json.dumps(d, indent=4))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline_run_uuid", required=True)
    parser.add_argument("--catreport_db_path", required=True)
    args = parser.parse_args()

    # get catreport database
    con = sqlite3.connect(args.catreport_db_path)
    con.row_factory = sqlite3.Row
    res_rows = con.execute(
        "select * from q where pipeline_run_uuid = ? and type = ?",
        (args.pipeline_run_uuid, "resistance"),
    )

    # create dictionary from sample_name to report json
    sample_json = dict()
    for row in res_rows:
        sample_name = row["sample_name"]
        if not pathlib.Path(row["report_filename"]).is_file():
            sys.stderr.write(
                f"report filename for {sample_name} doesn't exist: {row['report_filename']}. Are all the resistance reports finished?\n\n"
            )
            sys.exit(1)
        with open(row["report_filename"]) as f:
            try:
                sample_json[sample_name] = json.loads(f.read())
            except Exception as e:
                print(f"{row['report_filename']}: {str(e)}")

    a = perform_analysis(sample_json)
    save_analysis(a, args.pipeline_run_uuid)


if __name__ == "__main__":
    main()
