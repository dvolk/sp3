#! /usr/bin/env python

import argparse, os, pathlib, pickle, gzip, json

from copy import deepcopy

import pandas, numpy
from tqdm import tqdm

import gumpy, piezo

def mutations_assign_booleans(row):
    if row['POSITION']<0:
        is_cds=False
        is_promoter=True
    else:
        is_cds=True
        is_promoter=False
    if row['MUTATION'][0].isupper():
        if row['MUTATION'][0]==row['MUTATION'][-1]:
            is_synonymous=True
            is_nonsynonymous=False
        else:
            is_synonymous=False
            is_nonsynonymous=True
    else:
        is_synonymous=False
        is_nonsynonymous=False

    is_het=False
    is_null=False
    is_snp=False

    if row["MUTATION"][-1] in ['z','Z']:
        is_het=True
    elif row["MUTATION"][-1] in ['x','X']:
        is_null=True
    elif not row["IS_INDEL"]:
        is_snp=True

    return(pandas.Series([is_synonymous,is_nonsynonymous,is_het,is_null]))

def mutations_count_number_nucleotide_changes(row):
    if row['REF'] is not None and len(row['REF'])==3:
        return(numpy.sum([i!=j for (i,j) in zip(row['REF'],row['ALT'] ) ]))
    else:
        return(0)

def run(vcf_file,
        genome_object,
        catalogue_file,
        ignore_vcf_status,
        ignore_vcf_filter,
        progress,
        debug):
    if debug:
        print("Loading the reference object..")

    # load the pickled reference gumpy Genome object to save time
    INPUT=gzip.open(genome_object,"rb")
    reference_genome=pickle.load(INPUT)
    INPUT.close()

    # check the log folder exists (it probably does)
    pathlib.Path('logs/').mkdir(parents=True, exist_ok=True)

    if catalogue_file is not None:
        if debug:
            print("Instantiating a Resistance Catalogue..")

        # instantiate a Resistance Catalogue instance by passing a text file
        resistance_catalogue=piezo.ResistanceCatalogue(catalogue_file)

    if debug:
        print("Creating a sample Genome object by copying the reference Genome object...")

    # create a copy of the reference genome which we will then alter according to the VCF file
    # need a deepcopy to ensure we take all the private variables etc with us
    sample_genome=deepcopy(reference_genome)

    (vcf_folder,vcf_filename)=os.path.split(vcf_file)

    vcf_stem=vcf_file.split(".vcf")[0]

    metadata={}

    if debug:
        print("applying the VCF file to sample Genome...")


    sample_genome.apply_vcf_file( show_progress_bar=progress,\
                                  vcf_file=vcf_file,\
                                  ignore_status=ignore_vcf_status,\
                                  ignore_filter=ignore_vcf_filter,\
                                  metadata_fields=['GT_CONF','GT_CONF_PERCENTILE'])


    if debug:
        print("Creating the VARIANTS table..")

    VARIANT=sample_genome.table_variants_wrt(reference_genome)

    # only proceed if there are actually variants!
    if VARIANT is not None:

        VARIANT['UNIQUEID']=sample_genome.name

        # reorder the columns
        VARIANT=VARIANT[['UNIQUEID','VARIANT','REF','ALT','GENOME_INDEX','GENE','ELEMENT_TYPE',"MUTATION_TYPE",'POSITION','NUCLEOTIDE_NUMBER','AMINO_ACID_NUMBER','ASSOCIATED_WITH_GENE','GT_CONF_PERCENTILE','IN_PROMOTER','IN_CDS','IS_SNP','IS_INDEL','IS_HET','IS_NULL','INDEL_LENGTH',"INDEL_1","INDEL_2","COVERAGE","HET_VARIANT_0","HET_VARIANT_1","HET_COVERAGE_0","HET_COVERAGE_1","HET_INDEL_LENGTH_0","HET_INDEL_LENGTH_1","HET_REF","HET_ALT_0","HET_ALT_1","GT_CONF"]]

        # set the index
        VARIANT.set_index(['UNIQUEID','VARIANT','IS_SNP'],inplace=True,verify_integrity=True)

    if debug:
        print("Creating the MUTATIONS table..")

    MUTATIONS=None

    for gene in reference_genome.gene_names:

        # find out the mutations
        mutations=sample_genome.genes[gene].table_mutations_wrt(reference_genome.genes[gene])

        if mutations is not None:

            if MUTATIONS is not None:
                MUTATIONS=pandas.concat([MUTATIONS,mutations])
            else:
                MUTATIONS=mutations
    
    if MUTATIONS is not None:

        # define some Boolean columns for ease of analysis
        MUTATIONS[['IS_SYNONYMOUS','IS_NONSYNONYMOUS','IS_HET','IS_NULL']]=MUTATIONS.apply(mutations_assign_booleans,axis=1)

        # calculate the number of nucleotide changes required for this mutation
        MUTATIONS["NUMBER_NUCLEOTIDE_CHANGES"]=MUTATIONS.apply(mutations_count_number_nucleotide_changes,axis=1)

        MUTATIONS['UNIQUEID']=sample_genome.name

        MUTATIONS=MUTATIONS.astype( {'IS_SYNONYMOUS':'bool',\
                                     'IS_NONSYNONYMOUS':'bool',\
                                     'IS_HET':'bool',\
                                     'IS_NULL':'bool',\
                                     'NUMBER_NUCLEOTIDE_CHANGES':'int'})

        # reorder the columns
        # MUTATIONS=MUTATIONS[["UNIQUEID","GENE","MUTATION","POSITION","SITEID","MUTATION_TYPE","ELEMENT_TYPE","AMINO_ACID_NUMBER","NUCLEOTIDE_NUMBER","IN_PROMOTER","IN_CDS","IS_SYNONYMOUS","IS_NONSYNONYMOUS","IS_HET","IS_INDEL","IS_NULL","IS_SNP","REF","ALT","NUMBER_NUCLEOTIDE_CHANGES","INDEL_LENGTH","INDEL_1","INDEL_2"]]
        MUTATIONS=MUTATIONS[["UNIQUEID",'GENE','MUTATION','POSITION','AMINO_ACID_NUMBER','GENOME_INDEX','NUCLEOTIDE_NUMBER','REF','ALT','IS_SNP','IS_INDEL','IN_CDS','IN_PROMOTER','IS_SYNONYMOUS','IS_NONSYNONYMOUS','IS_HET','IS_NULL','ELEMENT_TYPE','MUTATION_TYPE','INDEL_LENGTH','INDEL_1','INDEL_2',"NUMBER_NUCLEOTIDE_CHANGES"]]
        # set the index
        MUTATIONS.set_index(["UNIQUEID","GENE",'MUTATION'],inplace=True,verify_integrity=True)

        MUTATIONS.reset_index(inplace=True)

    # add GT_CONF
    MUTATIONS.set_index(["GENE","POSITION"],inplace=True,verify_integrity=True)
    VARIANT.set_index(["GENE","POSITION"],inplace=True,verify_integrity=False)
    MUTATIONS=MUTATIONS.join(VARIANT[['GT_CONF']],how="inner")
    MUTATIONS.reset_index(inplace=True)
    VARIANT.reset_index(inplace=True)

        
    # by default assume wildtype behaviour so set all drug phenotypes to be susceptible
    phenotype={}
    for drug in resistance_catalogue.catalogue.drugs:
        phenotype[drug]="S"

    # can only infer predicted effects and ultimate phenotypes if a resistance catalogue has been supplied!
    if catalogue_file is not None and MUTATIONS is not None:

        # subset down to only those mutations in the catalogue for making predictions
        MUTATIONS_IN_CATALOGUE=MUTATIONS.loc[MUTATIONS.GENE.isin(resistance_catalogue.catalogue.genes)]


        EFFECTS_dict={}
        EFFECTS_counter=0

        for gene_name,mutation_name in zip(MUTATIONS_IN_CATALOGUE.GENE,MUTATIONS_IN_CATALOGUE.MUTATION):

            try:
                valid=reference_genome.valid_gene_mutation(gene_name+"@"+mutation_name)
            except:
                valid=False

            assert valid, gene_name+"@"+mutation_name+" is not a valid mutation!"

            prediction=resistance_catalogue.predict(gene_name+"@"+mutation_name)

            # if it isn't an S, then a dictionary must have been returned
            if prediction!="S":

                # iterate through the drugs in the dictionary (can be just one)
                for drug_name in prediction:

                    # only for completeness as this logic never leads to a change since by default the phenotype is S
                    if drug_name and prediction[drug_name]=="S" and phenotype[drug_name]=="S":
                        phenotype[drug_name]="S"

                    # if the prediction is a U, we only move to a U if the current prediction is S
                    # (to stop it overiding an R)
                    # (again for completeness including the superfluous state)
                    elif drug_name and prediction[drug_name]=="U" and phenotype[drug_name] in ["S","U"]:
                        phenotype[drug_name]="U"

                    # finally if an R is predicted, it must be R
                    elif drug_name and prediction[drug_name]=="R":
                        phenotype[drug_name]="R"

                    EFFECTS_dict[EFFECTS_counter]=[sample_genome.name,gene_name,mutation_name,resistance_catalogue.catalogue.name,drug_name,prediction[drug_name]]
                    EFFECTS_counter+=1
            else:
                EFFECTS_dict[EFFECTS_counter]=[sample_genome.name,gene_name,mutation_name,resistance_catalogue.catalogue.name,"UNK","S"]
                EFFECTS_counter+=1

        EFFECTS=pandas.DataFrame.from_dict(EFFECTS_dict,orient="index",columns=["UNIQUEID","GENE","MUTATION","CATALOGUE_NAME","DRUG","PREDICTION"])
        EFFECTS.set_index(["UNIQUEID","DRUG","GENE","MUTATION","CATALOGUE_NAME"],inplace=True)

    wgs_prediction_string=""
    for drug in resistance_catalogue.catalogue.drugs:
        metadata["WGS_PREDICTION_"+drug]=phenotype[drug]

    effects = list()
    for e in EFFECTS_dict.values():
        effects.append({ 'gene_name': e[1],
                         'mutation_name': e[2],
                         'drug_name': e[4],
                         'prediction': e[5] })
    
    mutations = list()
    for m in MUTATIONS_IN_CATALOGUE.to_dict('rows'):
        mutations.append({
            'genome_index': m['GENOME_INDEX'],
            'vcf_filename': None,
            'gene_name': m['GENE'],
            'variant_type': None,
            'mutation_name': m['MUTATION'],
            'element_type': m['ELEMENT_TYPE'],
            'position': m['POSITION'],
            'promoter': m['IN_PROMOTER'],
            'cds': m['IN_CDS'],
            'synonymous': m['IS_SYNONYMOUS'],
            'nonsynonymous': m['IS_NONSYNONYMOUS'],
            'insertion': None,
            'deletion': None,
            'ref': m['REF'],
            'alt': m['ALT'],
            'indel_1': m['INDEL_1'],
            'indel_2': m['INDEL_2'],
            'indel_3': None,
            'ref_coverage': None,
            'alt_coverage': None,
            'gt_conf': m['GT_CONF'],
            'minos_score': None,
            'number_nucleotide_changes': m['NUMBER_NUCLEOTIDE_CHANGES'] })

    return {
        'vcf_filepath': vcf_file,
        'metadata': metadata,
        'effects': effects,
        'mutations': mutations }
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vcf_file",required=True,help="the path to a single VCF file")
    parser.add_argument("--genome_object",default="H37Rv_3.pkl.gz",help="the path to a compressed pickled gumpy Genome object")
    parser.add_argument("--catalogue_file",default=None,required=False,help="the path to the resistance catalogue")
    parser.add_argument("--ignore_vcf_status",action='store_true',default=False,help="whether to ignore the STATUS field in the vcf (e.g. necessary for some versions of Clockwork VCFs)")
    parser.add_argument("--ignore_vcf_filter",action='store_true',default=False,help="whether to ignore the FILTER field in the vcf (e.g. necessary for some versions of Clockwork VCFs)")
    parser.add_argument("--progress",action='store_true',default=False,help="whether to show progress using tqdm")
    parser.add_argument("--debug",action='store_true',default=False,help="print progress statements to STDOUT to help debugging")
    options = parser.parse_args()

    print(run(options.vcf_file,
              options.genome_object,
              options.catalogue_file,
              options.ignore_vcf_status,
              options.ignore_vcf_filter,
              options.progress,
              options.debug))


if __name__ == "__main__":
    main()
