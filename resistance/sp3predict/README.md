# sp3predict

Simple script to make DST predictions given a (Clockwork) VCF, a catalogue and a gumpy genome object.

## Pre-requisities

1. [`gumpy`](https://github.com/oxfordmmm/gumpy)
2. [`piezo`](https://github.com/oxfordmmm/piezo)
3. One or more AMR catalogues in the format required by `piezo`. Several published tuberculosis catalogues are available in this [repo](https://github.com/oxfordmmm/tuberculosis_amr_catalogues)

A `gumpy` genome object is too large to easily store in a repo, so for example for *M. tuberculosis* we should first create a local copy from the supplied GenBank file using `gumpy-save-genome.py` which should be in your `$PATH` if you have already installed `gumpy`.

```
$ gumpy-save-genome.py --genbank_file config/H37rV_v3.gbk --name config/H37rV_v3.pkl
```
This will take about five minutes.

Now you are ready

```
$ sp3predict.py --vcf_file tests/test-cases/01/01.vcf,\
                --catalogue_file ../tuberculosis_amr_catalogues/catalogues/NC_000962.3/NC_000962.3_NEJM2018_v1.0_GARC1_RUS.csv,\
                --progress --ignore_vcf_status --ignore_vcf_filter --genome_object config/H37rV_v3.pkl.gz 
```

Note that since this VCF file comes from an old version of Clockwork which doesn't make use of the `STATUS` and `FILTER` columns, we have to tell the code to ignore these.

The output should be
```
                                VCF file tests/test-cases/01/01.vcf
                        Reference genome NC_000962.3
                          Catalogue name NEJM2018
                       Catalogue version v1.0
                       Catalogue grammar GARC1
                        Catalogue values ['R', 'U', 'S']
                          Catalogue path ../tuberculosis_amr_catalogues/catalogues/NC_000962.3/NC_000962.3_NEJM2018_v1.0_GARC1_RUS.csv
                             Genome file config/H37rV_v3.pkl.gz
                      WGS_PREDICTION_EMB R
                      WGS_PREDICTION_INH R
                      WGS_PREDICTION_PZA R
                      WGS_PREDICTION_RIF R
```
