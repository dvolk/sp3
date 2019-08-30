import os
from copy import deepcopy
from datetime import datetime

import piezo
import gemucator

def get_resistance_for_tb_sample(genbank_file, catalog_file, catalogue_name, resistance_log, sample_id, vcf_file):
    '''
    Instantiate a Resistance Catalogue instance by passing a text file')
    '''
    datestamp = datetime.strftime(datetime.now(), '%Y-%m-%d_%H%M')
    log_file = f"{resistance_log}{sample_id}_{datestamp}.csv"

    walker_catalogue = piezo.ResistanceCatalogue(input_file=catalog_file,
                                                 log_file=log_file,
                                                 genbank_file=genbank_file,
                                                 catalogue_name=catalogue_name)
    '''
    Retrieve the dictionary of genes from the Resistance Catalogue
    '''
    gene_panel = walker_catalogue.gene_panel

    '''
    Setup a GeneCollection object that contains all the genes/loci we are interested in
    '''
    wildtype_gene_collection = piezo.GeneCollection(species="M. tuberculosis",
                                                    genbank_file=genbank_file,
                                                    gene_panel=gene_panel,
                                                    log_file=log_file)

    '''
    Setup a Gemucator object so you can check the mutations are valid
    '''
    reference_genome = gemucator.gemucator(genbank_file=genbank_file)

    '''
    Create a copy of the wildtype_gene_collection genes which we will then alter according to the VCF file, 
    need a deepcopy to ensure we take all the private variables etc with us, and point just take pointers
    '''
    sample_gene_collection = deepcopy(wildtype_gene_collection)

    vcf_filename = os.path.split(vcf_file)[1]

    n_hom, n_het, n_ref, n_null = sample_gene_collection.apply_vcf_file(vcf_file)

    '''
    Store some useful features
    '''
    metadata = dict()
    metadata = { "GENOME_N_HOM": n_hom,
                 "GENOME_N_HET": n_het,
                 "GENOME_N_REF": n_ref,
                 "GENOME_N_NULL": n_null }

    '''
    By default assume wildtype behaviour so set all drug phenotypes to be susceptible
    '''
    phenotype = dict()
    for drug in walker_catalogue.drug_list:
        phenotype[drug] = "S"

    MUTATIONS_list = list()
    EFFECTS_list = list()

    '''
    Get all the genes to calculate their own differences w.r.t the references, i.e. their mutations!
    '''
    for gene_name in wildtype_gene_collection.gene_panel:
        '''
        now we pass the wildtype_gene_collection gene so our VCF gene can calculate its mutations
        '''
        sample_gene_collection.gene[gene_name].identify_mutations(wildtype_gene_collection.gene[gene_name])

        mutations = sample_gene_collection.gene[gene_name].mutations

        for mutation_name in mutations:
            MUTATIONS_list.append({ "vcf_filename": vcf_filename,
                                    "gene_name": gene_name,
                                    "variant_type": mutations[mutation_name]["VARIANT_TYPE"],
                                    "mutation_name": mutation_name,

                                    "element_type": mutations[mutation_name]["ELEMENT_TYPE"],
                                    "position": int(mutations[mutation_name]["POSITION"]),
                                    "promoter": mutations[mutation_name]["PROMOTER"],

                                    "cds": mutations[mutation_name]["CDS"],
                                    "synonymous": mutations[mutation_name]["SYNONYMOUS"],
                                    "nonsynonymous": mutations[mutation_name]["NONSYNONYMOUS"],

                                    "insertion": mutations[mutation_name]["INSERTION"],
                                    "deletion": mutations[mutation_name]["DELETION"],
                                    "ref": mutations[mutation_name]["REF"],

                                    "alt": mutations[mutation_name]["ALT"],
                                    "indel_1": mutations[mutation_name]["INDEL_1"],
                                    "indel_2": mutations[mutation_name]["INDEL_2"],
                                    "indel_3": mutations[mutation_name]["INDEL_3"],

                                    "ref_coverage": int(mutations[mutation_name]["REF_COVERAGE"]),
                                    "alt_coverage": int(mutations[mutation_name]["ALT_COVERAGE"]),
                                    "minos_score": float(mutations[mutation_name]["MINOS_SCORE"]),
                                    "number_nucleotide_changes": str(mutations[mutation_name]["NUMBER_NUCLEOTIDE_CHANGES"]) })

            gene_mutation = f"{gene_name}_{mutation_name}"

            if reference_genome.valid_mutation(gene_mutation):
                prediction = walker_catalogue.predict(gene_mutation=gene_mutation, verbose=False)
                # if it isn't an S, then a dictionary must have been returned
                if prediction != "S":
                    # iterate through the drugs in the dictionary (can be just one)
                    for drug_name in prediction:
                        tmp_effect = setDefaulEffect(vcf_filename, gene_name, mutation_name)
                        # only for completeness as this logic never leads to a change since by default the phenotype is S
                        if drug_name and prediction[drug_name] == "S" and phenotype[drug_name] == "S":
                            phenotype[drug_name] = "S"
                        # if the prediction is a U, we only move to a U if the current prediction is S
                        # (to stop it overiding an R)
                        # (again for completeness including the superfluous state)
                        elif drug_name and prediction[drug_name] =="U" and phenotype[drug_name] in ["S", "U"]:
                            phenotype[drug_name] = "U"
                        # finally if an R is predicted, it must be R
                        elif drug_name and prediction[drug_name] =="R":
                            phenotype[drug_name] = "R"

                        tmp_effect["drug_name"] = drug_name
                        tmp_effect["prediction"] = prediction[drug_name]
                        EFFECTS_list.append(tmp_effect)
                else:
                    tmp_effect = setDefaulEffect(vcf_filename, gene_name, mutation_name)
                    EFFECTS_list.append(tmp_effect)

    for drug in walker_catalogue.drug_list:
        metadata["WGS_PREDICTION_" + drug] = phenotype[drug]

    return { "metadata": metadata,
             "mutations": MUTATIONS_list,
             "effects": EFFECTS_list }

def setDefaulEffect(vcf_filename, gene_name, mutation_name):
    return { "vcf_filename": vcf_filename,
             "gene_name": gene_name,
             "mutation_name": mutation_name,
             "drug_name": "UNK",
             "prediction": "U" }
