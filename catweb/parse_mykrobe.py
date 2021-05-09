#!/usr/bin/env python3
# Mykrobe explained: https://github.com/Mykrobe-tools/mykrobe
#python3 parse_mykrobe.py -m  data/mykrobe3.json -o output/mykrobe3.json
import sys
import json
import argparse
from collections import defaultdict

def report_species(mykrobe_data):
    result = defaultdict(dict)

    susceptibility = mykrobe_data['tb_sample_id']['susceptibility']
    result['susceptibility'] = susceptibility

    data = mykrobe_data['tb_sample_id']['phylogenetics']

    result['mykrobe-predictor_version'] = mykrobe_data['tb_sample_id']['version']['mykrobe-predictor']
    result['mykrobe-atlas_version'] = mykrobe_data['tb_sample_id']['version']['mykrobe-atlas']
    result['phylo_group'] = data['phylo_group']
    result['sub_complex'] = data['sub_complex']
    result['species'] = data['species']

    try:
        lineages = data['lineage']['lineage']
        result['lineages'] = lineages
        for lineage in lineages:
            r_lineages = defaultdict()
            l_calls = data['lineage']['calls'][lineage]
            for k, v in l_calls.items():
                mutations = dict()
                if v != None:
                    for mut,mut_info in v.items():
                        coverage = mut_info['info']['coverage']['alternate']
                        mutations[mut] = coverage
                    r_lineages[k] = mutations
                result[lineage] = r_lineages
    except:
        # couldn't process lineage. pre 0.9 mykrobe?
        pass
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mykrobe_file", help="mykrobe output file")
    parser.add_argument("-o", "--output_file", default='output.json', help="output json file, default output.json")
    args = parser.parse_args()
    with open(args.mykrobe_file) as mykrobe:
        data = json.load(mykrobe)
    pretty_output = json.dumps(report_species(data), indent=4)
    print(pretty_output)

    with open(args.output_file, 'w') as outfile:
        outfile.write(pretty_output)
