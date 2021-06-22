# Create CSV files from object store

Simple tool to generate CSV files for nextflow workflow to take from object store.
Assumes object store files have metadata including run and sampleID

```bash
python3 sp3/download-api/oci_utils/getFiles.py  -o /data/inputs/
```

Creates csv files in `/data/inputs/runs` and `/data/inputs/runs/samples` with the format as such:

```
SAMPLE NAME, BUCKET NAME, FILE NAME
LC25_barcode01,test_nanopore_samples,metaLC25_barcode01_r0barcode01b0.fastq.gz
LC25_barcode01,test_nanopore_samples,metaLC25_barcode01_r0barcode01b1.fastq.gz
LC25_barcode02,test_nanopore_samples,metaLC25_barcode02_r0barcode02b0.fastq.gz
LC25_barcode02,test_nanopore_samples,metaLC25_barcode02_r0barcode02b1.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b0.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b1.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b10.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b11.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b2.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b3.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b4.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b5.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b6.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b7.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b8.fastq.gz
LC25_barcode03,test_nanopore_samples,metaLC25_barcode03_r0barcode03b9.fastq.gz
LC25_barcode04,test_nanopore_samples,metaLC25_barcode04_r0barcode04b0.fastq.gz
LC25_barcode04,test_nanopore_samples,metaLC25_barcode04_r0barcode04b1.fastq.gz
LC25_barcode04,test_nanopore_samples,metaLC25_barcode04_r0barcode04b10.fastq.gz
```


