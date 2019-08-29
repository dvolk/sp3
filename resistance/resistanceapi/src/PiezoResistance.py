#! /usr/bin/python3.5
import argparse, os
from copy import deepcopy
from datetime import datetime
import pandas
from tqdm import tqdm
import piezo
import gemucator
from helper import logger

import functools

class PiezoResistance():
    @staticmethod
    def getResistanceForSample(genbank_file,catalog_file,catalogue_name,resistance_log,sample_id,vcf_file):                
        datestamp = datetime.strftime(datetime.now(), '%Y-%m-%d_%H%M')
        log_file = resistance_log + sample_id + "_" + datestamp + ".csv"
        logger.info('Create a datestamp for piezo log files: ' + log_file)
        logger.info('Instantiate a Resistance Catalogue instance by passing a text file')
        walker_catalogue=piezo.ResistanceCatalogue(input_file= catalog_file,log_file=log_file,genbank_file=genbank_file,catalogue_name=catalogue_name)
        logger.info('Retrieve the dictionary of genes from the Resistance Catalogue')
        gene_panel=walker_catalogue.gene_panel

        logger.info('Setup a GeneCollection object that contains all the genes/loci we are interested in')
        wildtype_gene_collection=piezo.GeneCollection(species="M. tuberculosis",genbank_file=genbank_file,gene_panel=gene_panel,log_file=log_file)

        logger.info('Setup a Gemucator object so you can check the mutations are valid')
        reference_genome=gemucator.gemucator(genbank_file=genbank_file)

        logger.info('Create a copy of the wildtype_gene_collection genes which we will then alter according to the VCF file, need a deepcopy to ensure we take all the private variables etc with us, and point just take pointers')
        sample_gene_collection=deepcopy(wildtype_gene_collection)

        vcf_filename=os.path.split(vcf_file)[1]
        metadata={}
        (n_hom,n_het,n_ref,n_null)=sample_gene_collection.apply_vcf_file(vcf_file)

        logger.info('Store some useful features')
        metadata["GENOME_N_HOM"]=n_hom
        metadata["GENOME_N_HET"]=n_het
        metadata["GENOME_N_REF"]=n_ref
        metadata["GENOME_N_NULL"]=n_null

        logger.info('By default assume wildtype behaviour so set all drug phenotypes to be susceptible')
        phenotype={}
        for drug in walker_catalogue.drug_list:
            phenotype[drug]="S"

        MUTATIONS_list=[]        
        EFFECTS_list=[]

        logger.info('Get all the genes to calculate their own differences w.r.t the references, i.e. their mutations!')
        for gene_name in wildtype_gene_collection.gene_panel:
            # now we pass the wildtype_gene_collection gene so our VCF gene can calculate its mutations
            sample_gene_collection.gene[gene_name].identify_mutations(wildtype_gene_collection.gene[gene_name])
            mutations=sample_gene_collection.gene[gene_name].mutations
            for mutation_name in mutations:
                tmp_mutation = {}
                tmp_mutation["vcf_filename"] = vcf_filename
                tmp_mutation["gene_name"] = gene_name
                tmp_mutation["variant_type"] = mutations[mutation_name]["VARIANT_TYPE"]
                tmp_mutation["mutation_name"] = mutation_name

                tmp_mutation["element_type"] = mutations[mutation_name]["ELEMENT_TYPE"]
                tmp_mutation["position"] = int(mutations[mutation_name]["POSITION"])
                tmp_mutation["promoter"] = mutations[mutation_name]["PROMOTER"]

                tmp_mutation["cds"] = mutations[mutation_name]["CDS"]
                tmp_mutation["synonymous"] = mutations[mutation_name]["SYNONYMOUS"]
                tmp_mutation["nonsynonymous"] = mutations[mutation_name]["NONSYNONYMOUS"]

                tmp_mutation["insertion"] = mutations[mutation_name]["INSERTION"]
                tmp_mutation["deletion"] = mutations[mutation_name]["DELETION"]
                tmp_mutation["ref"] = mutations[mutation_name]["REF"]

                tmp_mutation["alt"] = mutations[mutation_name]["ALT"]
                tmp_mutation["indel_1"] = mutations[mutation_name]["INDEL_1"]
                tmp_mutation["indel_2"] = mutations[mutation_name]["INDEL_2"]
                tmp_mutation["indel_3"] = mutations[mutation_name]["INDEL_3"]

                tmp_mutation["ref_coverage"] = int(mutations[mutation_name]["REF_COVERAGE"])
                tmp_mutation["alt_coverage"] = int(mutations[mutation_name]["ALT_COVERAGE"])
                tmp_mutation["minos_score"] = float(mutations[mutation_name]["MINOS_SCORE"])
                tmp_mutation["number_nucleotide_changes"] = str(mutations[mutation_name]["NUMBER_NUCLEOTIDE_CHANGES"])

                MUTATIONS_list.append(tmp_mutation)
                gene_mutation = gene_name + "_" + mutation_name
                if reference_genome.valid_mutation(gene_mutation):
                    prediction=walker_catalogue.predict(gene_mutation=gene_mutation,verbose=False)
                    # if it isn't an S, then a dictionary must have been returned
                    if prediction!="S":
                        # iterate through the drugs in the dictionary (can be just one)
                        for drug_name in prediction:
                            tmp_effect = PiezoResistance.setDefaulEffect(vcf_filename,gene_name,mutation_name) 
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

                            tmp_effect["drug_name"] = drug_name
                            tmp_effect["prediction"] = prediction[drug_name]
                            EFFECTS_list.append(tmp_effect)
                    else:
                        tmp_effect = PiezoResistance.setDefaulEffect(vcf_filename,gene_name,mutation_name)
                        EFFECTS_list.append(tmp_effect)                    
        
        for drug in walker_catalogue.drug_list:
            metadata["WGS_PREDICTION_"+drug]=phenotype[drug]
        rs={}
        rs["metadata"]=metadata
        rs["mutations"]=MUTATIONS_list
        rs["effects"]=EFFECTS_list
        logger.info('Return results')
        return rs  
    
    @staticmethod
    def setDefaulEffect(vcf_filename,gene_name,mutation_name):
        effect = {}
        effect["vcf_filename"]=vcf_filename
        effect["gene_name"]=gene_name
        effect["mutation_name"]=mutation_name
        effect["drug_name"]="UNK"
        effect["prediction"]="U"
        return effect     
