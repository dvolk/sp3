"""
Helper functions for resistance
"""

import collections
import fnmatch
import functools
import logging


def resistance_postprocess(report_data):
    for i, item in enumerate(report_data["resistance"]["data"]["effects"]):
        mut = item["gene_name"] + "_" + item["mutation_name"]
        drug = item["drug_name"]
        source = gene_to_source(mut, drug)[1]
        logging.debug(mut, source)
        report_data["resistance"]["data"]["effects"][i]["source"] = source

    def is_ok_mutation(eff):
        """
        Mutations where the mutation does nothing or ends in a z are 'not ok' cf Tim Peto
        """
        if eff["mutation_name"][0] == eff["mutation_name"][-1] or eff["mutation_name"][
            -1
        ] in ["z", "Z"]:
            return False
        else:
            return True

    def drug_prediction(effects, drug_name):
        """
        this returns the resistance prediction for drug

        Although the piezo resistance prediction already includes a prediction, we include
        some extra logic to add the F (failed) prediction.
        """
        drug_effects = [x for x in effects if drug_name == x["drug_name"]]
        """
        Also, group the effects under drug name
        """
        # TODO
        template_report_data["resistance"]["data"][drug_name] = drug_effects

        """
        No effects = S
        """
        if not drug_effects:
            return "S"

        """
        All effects are S = S
        """
        all_S = True
        for eff in drug_effects:
            if eff["prediction"] != "S":
                all_S = False
                break
        if all_S:
            return "S"

        """
        At least one R that is an ok mutation = R
        """
        one_ok_R = False
        for eff in drug_effects:
            if eff["prediction"] == "R" and is_ok_mutation(eff):
                one_ok_R = True
                break
        if one_ok_R:
            return "R"

        """
        At least one R that is not an ok mutation = F
        """
        one_bad_R = False
        for eff in drug_effects:
            if eff["prediction"] == "R" and not is_ok_mutation(eff):
                one_bad_R = True
                break
        if one_bad_R:
            return "F"

        """
        No Rs and all U are bad mutations = S
        """
        all_bad_U = True
        for eff in drug_effects:
            if eff["prediction"] == "U" and is_ok_mutation(eff):
                all_bad_U = False
        if all_bad_U:
            return "S"

        """
        All other cases = U
        """
        return "U"

    template_report_data = dict()
    template_report_data["resistance"] = dict()
    template_report_data["resistance"]["data"] = dict()
    template_report_data["resistance"]["data"][
        "resistance_effects"
    ] = collections.defaultdict(list)
    template_report_data["resistance"]["data"][
        "res_rev_index"
    ] = collections.defaultdict(
        list
    )  # gene_mutation -> item

    template_report_data["resistance"]["data"]["effects"] = report_data["resistance"][
        "data"
    ]["effects"]
    template_report_data["resistance"]["data"]["mutations"] = report_data["resistance"][
        "data"
    ]["mutations"]

    template_report_data["resistance"]["data"]["prediction_ex"] = dict()
    for drug_name in ["INH", "RIF", "PZA", "EMB", "AMI", "KAN", "LEV", "STM"]:
        template_report_data["resistance"]["data"]["prediction_ex"][
            drug_name
        ] = drug_prediction(report_data["resistance"]["data"]["effects"], drug_name)

    for item in report_data["resistance"]["data"]["effects"]:
        if is_ok_mutation(item):
            full_name = item["gene_name"] + "_" + item["mutation_name"]
            drug_name = item["drug_name"]
            template_report_data["resistance"]["data"]["resistance_effects"][
                drug_name
            ].append(item)
            template_report_data["resistance"]["data"]["res_rev_index"][
                full_name
            ].append(item)

    return template_report_data["resistance"]["data"]


def get_phylosnp_blacklist():
    phylosnp_blacklist_file = "/data/reports/resistance/misc/phylosnp_blacklist.txt"
    phylosnp_blacklist = [x.strip() for x in open(phylosnp_blacklist_file).readlines()]
    return phylosnp_blacklist


phylosnp_blacklist = get_phylosnp_blacklist()


def get_catalog():
    catalog_file = "/data/reports/resistance/misc/catalog.txt"
    catalog = [
        x.strip().split("\t") for x in open(catalog_file).readlines() if x[0] != "#"
    ]
    """
    add source to phylosnps and mark them sensitive
    """
    for x in catalog:
        if x[1] in phylosnp_blacklist:
            x[0] = "phylosnp"
    return catalog


catalog = get_catalog()


@functools.lru_cache(maxsize=None)
def gene_to_source(gene_name, drug_name):
    """
    For a given gene + mutation, find the catalog source
    """
    print(gene_name, drug_name)

    """
    try to find exact match
    """
    for catalog_line in catalog:
        catalog_gene_name = catalog_line[1]
        catalog_drug_name = catalog_line[2]
        if catalog_gene_name == gene_name and catalog_drug_name == drug_name:
            catalog_gene_source = catalog_line[0]
            return catalog_gene_name, catalog_gene_source

    """
    try to find fuzzy match
    """
    for catalog_line in catalog:
        catalog_gene_name = catalog_line[1]
        catalog_drug_name = catalog_line[2]
        if catalog_drug_name == drug_name and fnmatch.fnmatch(
            gene_name, catalog_gene_name
        ):
            catalog_gene_source = catalog_line[0]
            return catalog_gene_name, catalog_gene_source

    """
    nothing found
    """
    return "", ""
