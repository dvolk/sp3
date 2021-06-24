import collections
import json
import pathlib
import sqlite3
import sys

import pandas
import pymysql


def get_reports():
    con = sqlite3.connect("/db/catreport.sqlite")
    con.row_factory = sqlite3.Row
    reports_rows = con.execute("select * from q").fetchall()
    return group_reports_by_sample(reports_rows)


def group_reports_by_sample(reports_rows):
    samples = collections.defaultdict(dict)
    for report_row in reports_rows:
        sample_unique_id = (
            report_row["pipeline_run_uuid"] + "/" + report_row["sample_name"]
        )
        report_type = report_row["type"]
        report_filename = report_row["report_filename"]
        if pathlib.Path(report_filename).is_file():
            samples[sample_unique_id][report_type] = dict(report_row)
    return samples


def extract_samtools_qc_data(report_row):
    lines = open(report_row["report_filename"]).readlines()
    data = dict()
    for line in lines:
        elems = line.strip().split("\t")
        if elems[0] == "SN":
            data[elems[1]] = elems[2]
    return data


def extract_resistance_data(report_row):
    content = open(report_row["report_filename"]).read()
    try:
        content = json.loads(content)
    except:
        return dict()
    try:
        return content["data"]["metadata"]
    except:
        return dict()


def extract_mykrobe_data(report_row):
    content = open(report_row["report_filename"]).read()
    try:
        content = json.loads(content)
    except:
        return dict()
    data = dict()
    return content["tb_sample_id"]["phylogenetics"]


def extract_kraken2_data(report_row):
    tbl = pandas.read_csv(
        report_row["report_filename"],
        sep="\t",
        header=None,
        names=[
            "RootFragments%",
            "RootFragments",
            "DirectFragments",
            "Rank",
            "NCBI_Taxonomic_ID",
            "Name",
        ],
    )
    # remove leading spaces from name
    tbl["Name"] = tbl["Name"].apply(lambda x: x.strip())
    data = dict()
    data["family"] = tbl.query('Rank == "F"').head(n=1).to_dict(orient="records")
    data["genus"] = tbl.query('Rank == "G"').head(n=1).to_dict(orient="records")
    data["species"] = tbl.query('Rank == "S"').head(n=1).to_dict(orient="records")
    data["human"] = (
        tbl.query('Name == "Homo sapiens"').head(n=1).to_dict(orient="records")
    )
    data["mycobacteriaceae"] = (
        tbl.query('Name == "Mycobacteriaceae"').head(n=1).to_dict(orient="records")
    )
    return data


def extract_pick_reference_data(report_row):
    content = open(report_row["report_filename"]).read()
    try:
        content = json.loads(content)
    except:
        return dict()
    return content


def process_samples(samples):
    dispatch = {
        "pick_reference": extract_pick_reference_data,
        "kraken2_speciation": extract_kraken2_data,
        "mykrobe_speciation": extract_mykrobe_data,
        "resistance": extract_resistance_data,
        "samtools_qc": extract_samtools_qc_data,
    }

    reports_data = collections.defaultdict(dict)
    for unique_id, reports in samples.items():
        for report_type, report_row in reports.items():
            #            if report_row['sample_name'] == '0384109a-885f-4cc5-a0e8-83e35922b08d':
            print(dispatch[report_type].__name__, report_row["report_filename"])
            report_data = dispatch[report_type](report_row)
            reports_data[unique_id][report_type] = report_data
    return reports_data


def insert_samples_sqlite(samples):
    con2 = sqlite3.connect("test.sqlite")
    con2.set_trace_callback(print)
    con2.execute("delete from test")

    for unique_id, report_data in reports_data.items():
        pipeline_run_uuid, sample_name = unique_id.split("/")
        con2.execute(
            "insert into test (pipeline_run_uuid, sample_name) values (?, ?)",
            (pipeline_run_uuid, sample_name),
        )
        if "samtools_qc" in report_data:
            samtools_qc_cols = [
                "samtools_qc_raw_total_sequences",
                "samtools_qc_reads_mapped",
                "samtools_qc_reads_paired",
                "samtools_qc_read_properly_paired",
                "samtools_qc_reads_qc_failed",
                "samtools_qc_error_rate",
                "samtools_qc_average_length",
                "samtools_qc_average_quality",
            ]
            samtools_qc_keys = [
                "raw total sequences:",
                "reads mapped:",
                "reads paired:",
                "reads properly paired:",
                "reads QC failed:",
                "error rate:",
                "average length:",
                "average quality:",
            ]
            samtools_cols_stmt = "".join([x + " = ?," for x in samtools_qc_cols])[:-1]
            con2.execute(
                f"update test set {samtools_cols_stmt} where pipeline_run_uuid = ? and sample_name = ?",
                (
                    *[report_data["samtools_qc"][x] for x in samtools_qc_keys],
                    pipeline_run_uuid,
                    sample_name,
                ),
            )

        if "resistance" in report_data:
            resistance_keys = report_data["resistance"].keys()
            resistance_cols = "".join(
                [
                    "resistance_" + x + " = ?,"
                    for x in resistance_keys
                    if "SNPIT" not in x
                ]
            )[:-1]
            if resistance_keys:
                # print(report_data)
                params = (
                    *[
                        report_data["resistance"][x]
                        for x in resistance_keys
                        if "SNPIT" not in x
                    ],
                    pipeline_run_uuid,
                    sample_name,
                )
                # print(params)
                # print('\n')
                # print(resistance_cols)
                con2.execute(
                    f"update test set {resistance_cols} where pipeline_run_uuid = ? and sample_name = ?",
                    params,
                )

        if "kraken2_speciation" in report_data:
            for k, v in report_data["kraken2_speciation"].items():
                if v:
                    con2.execute(
                        f"update test set kraken2_{k} = ?, kraken2_{k}_direct_fragments = ?, kraken2_{k}_root_fragments = ? where pipeline_run_uuid = ? and sample_name = ?",
                        (
                            v[0]["Name"],
                            v[0]["RootFragments"],
                            v[0]["DirectFragments"],
                            pipeline_run_uuid,
                            sample_name,
                        ),
                    )

        if "mykrobe_speciation" in report_data:
            for k, v in report_data["mykrobe_speciation"].items():
                for k2, v2 in v.items():
                    con2.execute(
                        f"update test set mykrobe_{k} = ?, mykrobe_{k}_percent_coverage = ?, mykrobe_{k}_median_depth = ? where pipeline_run_uuid = ? and sample_name = ?",
                        (
                            k2,
                            v2["percent_coverage"],
                            v2["median_depth"],
                            pipeline_run_uuid,
                            sample_name,
                        ),
                    )

        if "pick_reference" in report_data:
            con2.execute(
                "update test set pick_reference_tax_id = ? where pipeline_run_uuid = ? and sample_name = ?",
                (
                    report_data["pick_reference"]["pick_taxid"],
                    pipeline_run_uuid,
                    sample_name,
                ),
            )

        con2.commit()
        print(pipeline_run_uuid, sample_name)
        # print('\n\n')


def insert_samples_pymysql(samples):
    con3 = pymysql.connect(
        host="10.151.229.64",
        user="denis",
        password="denis08Aug2019",
        db="labkey_external_data_source",
    )
    con2 = con3.cursor()

    for unique_id, report_data in reports_data.items():
        pipeline_run_uuid, sample_name = unique_id.split("/")
        con2.execute(
            "insert into lsb_reports (pipeline_run_uuid, sample_name) values (%s, %s)",
            (pipeline_run_uuid, sample_name),
        )
        if "samtools_qc" in report_data:
            samtools_qc_cols = [
                "samtools_qc_raw_total_sequences",
                "samtools_qc_reads_mapped",
                "samtools_qc_reads_paired",
                "samtools_qc_read_properly_paired",
                "samtools_qc_reads_qc_failed",
                "samtools_qc_error_rate",
                "samtools_qc_average_length",
                "samtools_qc_average_quality",
            ]
            samtools_qc_keys = [
                "raw total sequences:",
                "reads mapped:",
                "reads paired:",
                "reads properly paired:",
                "reads QC failed:",
                "error rate:",
                "average length:",
                "average quality:",
            ]
            samtools_cols_stmt = "".join([x + " = %s," for x in samtools_qc_cols])[:-1]
            con2.execute(
                f"update lsb_reports set {samtools_cols_stmt} where pipeline_run_uuid = %s and sample_name = %s",
                (
                    *[report_data["samtools_qc"][x] for x in samtools_qc_keys],
                    pipeline_run_uuid,
                    sample_name,
                ),
            )

        if "resistance" in report_data:
            resistance_keys = report_data["resistance"].keys()
            resistance_cols = "".join(
                [
                    "resistance_" + x + " = %s,"
                    for x in resistance_keys
                    if "SNPIT" not in x
                ]
            )[:-1]
            if resistance_keys:
                params = (
                    *[
                        report_data["resistance"][x]
                        for x in resistance_keys
                        if "SNPIT" not in x
                    ],
                    pipeline_run_uuid,
                    sample_name,
                )
                con2.execute(
                    f"update lsb_reports set {resistance_cols} where pipeline_run_uuid = %s and sample_name = %s",
                    params,
                )

        if "kraken2_speciation" in report_data:
            for k, v in report_data["kraken2_speciation"].items():
                if v:
                    con2.execute(
                        f"update lsb_reports set kraken2_{k} = %s, kraken2_{k}_direct_fragments = %s, kraken2_{k}_root_fragments = %s where pipeline_run_uuid = %s and sample_name = %s",
                        (
                            v[0]["Name"],
                            v[0]["RootFragments"],
                            v[0]["DirectFragments"],
                            pipeline_run_uuid,
                            sample_name,
                        ),
                    )

        if "mykrobe_speciation" in report_data:
            for k, v in report_data["mykrobe_speciation"].items():
                for k2, v2 in v.items():
                    con2.execute(
                        f"update lsb_reports set mykrobe_{k} = %s, mykrobe_{k}_percent_coverage = %s, mykrobe_{k}_median_depth = %s where pipeline_run_uuid = %s and sample_name = %s",
                        (
                            k2,
                            v2["percent_coverage"],
                            v2["median_depth"],
                            pipeline_run_uuid,
                            sample_name,
                        ),
                    )

        if "pick_reference" in report_data:
            con2.execute(
                "update lsb_reports set pick_reference_tax_id = %s where pipeline_run_uuid = %s and sample_name = %s",
                (
                    report_data["pick_reference"]["pick_taxid"],
                    pipeline_run_uuid,
                    sample_name,
                ),
            )

        con3.commit()
        print(pipeline_run_uuid, sample_name)
        # print('\n\n')


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "push_report_rows":
        samples = get_reports()
        reports_data = process_samples(samples)
        insert_samples_pymysql(reports_data)
    if cmd == "push_vcf_rows":
        pass
