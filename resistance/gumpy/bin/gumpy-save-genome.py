#! /usr/bin/python3

import argparse

import gumpy

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--genbank_file", required=True, help="the path to a single VCF file"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="the path to a compressed pickled gumpy Genome object",
    )
    options = parser.parse_args()

    # instantiate a gumpy Genome object using the provided Genbank file
    reference_genome = gumpy.Genome(
        genbank_file=options.genbank_file, show_progress_bar=True, name=options.name
    )

    # save a compressed pickle to disc
    reference_genome.save_pickle(
        filename=options.name, compression=True, compresslevel=3
    )

    print(reference_genome)
