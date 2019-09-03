'''
Helper functions for resistance
'''

import functools
import fnmatch

def get_phylosnp_blacklist():
    phylosnp_blacklist_file = '/data/reports/resistance/data/phylosnp_blacklist.txt'
    phylosnp_blacklist = [x.strip() for x in open(phylosnp_blacklist_file).readlines()]
    return phylosnp_blacklist

phylosnp_blacklist = get_phylosnp_blacklist()

def get_catalog():
    catalog_file = '/data/reports/resistance/data/catalog.txt'
    catalog = [x.strip().split('\t') for x in open(catalog_file).readlines() if x[0] != '#']
    '''
    add source to phylosnps and mark them sensitive
    '''
    for x in catalog:
        if x[1] in phylosnp_blacklist:
            x[0] = 'phylosnp'
    return catalog

catalog = get_catalog()

@functools.lru_cache(maxsize=None)
def gene_to_source(gene_name, drug_name):
    '''
    For a given gene + mutation, find the catalog source
    '''
    print(gene_name, drug_name)

    '''
    try to find exact match
    '''
    for catalog_line in catalog:
        catalog_gene_name = catalog_line[1]
        catalog_drug_name = catalog_line[2]
        if catalog_gene_name == gene_name and catalog_drug_name == drug_name:
            catalog_gene_source = catalog_line[0]
            return catalog_gene_name, catalog_gene_source

    '''
    try to find fuzzy match
    '''
    for catalog_line in catalog:
        catalog_gene_name = catalog_line[1]
        catalog_drug_name = catalog_line[2]
        if catalog_drug_name == drug_name and fnmatch.fnmatch(gene_name, catalog_gene_name):
            catalog_gene_source = catalog_line[0]
            return catalog_gene_name, catalog_gene_source

    '''
    nothing found
    '''
    return "", ""
