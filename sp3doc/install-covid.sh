#! /bin/bash

# pull the singularity images from object storage
oci os object get -bn artic_images --name artic-ncov2019-illumina.sif --file artic-ncov2019-illumina.sif
sudo mv artic-ncov2019-illumina.sif /data/images/
oci os object get -bn artic_images --name artic-ncov2019-nanopore.sif --file artic-ncov2019-nanopore.sif
sudo mv artic-ncov2019-nanopore.sif /data/images/
sudo chown root /data/images/artic-ncov2019-*
sudo chgrp root /data/images/artic-ncov2019-*

oci os object get -bn upload_samples --name 210204_M01746_0015_000000000-JHB5M.tar --file 210204_M01746_0015_000000000-JHB5M.tar
sudo mkdir /data/inputs/uploads/oxforduni
sudo mv 210204_M01746_0015_000000000-JHB5M.tar /data/inputs/uploads/oxforduni/
cd /data/inputs/uploads/oxforduni/
sudo tar xvf 210204_M01746_0015_000000000-JHB5M.tar
sudo rm 210204_M01746_0015_000000000-JHB5M.tar

cd /data/pipelines/
sudo git clone https://github.com/oxfordmmm/ncov2019-artic-nf.git

