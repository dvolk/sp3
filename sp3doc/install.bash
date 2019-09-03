#!/bin/bash

set -e

#
# Check if we're running the right OS
#
if [ "$(cat /etc/issue | head -c 12)" != "Ubuntu 18.04" ]; then
    echo "*** This installation script requires Ubuntu 18.04."
    exit 1
fi

cd ..

SP3PREFIX=$(pwd)
USERNAME=$(whoami)

#
# ubuntu 18.04 package manager prerequisites
#
sudo apt update
sudo apt install etckeeper
sudo apt install build-essential python3-virtualenv virtualenv openjdk-8-jre-headless openvpn libpython3-all-dev libmysqlclient-dev

#
# nextflow
#
wget https://github.com/nextflow-io/nextflow/releases/download/v18.10.1/nextflow-18.10.1-all -O nextflow
sudo mv nextflow /usr/bin
sudo chmod a+x /usr/bin/nextflow

#
# python virtualenv
#
cd ..
virtualenv -p python3 env
source env/bin/activate
cd sp3

#
# sp3 packages
#
pip3 install -r requirements.txt

#
# resistance packages
#
cd $SP3PREFIX/resistance/gemucator
pip3 install .
cd $SP3PREFIX/resistance/piezo
pip3 install .


#
# copy slurm emu files to /usr/bin
#
sudo cp $SP3PREFIX/catgrid/tools/slurm_emu/* /usr/bin
sudo chmod a+x /usr/bin/{sbatch,squeue,scancel}

#
# create directories under /data
#
sudo mkdir -p /data/images
sudo mkdir -p /data/pipelines
sudo mkdir -p /data/references
sudo mkdir -p /data/reports/resistance/data
sudo mkdir -p /data/fetch
sudo mkdir -p /data/inputs
sudo mkdir -p /data/databases

sudo chown $USERNAME -R /data/fetch
sudo chown $USERNAME -R /data/inputs

#
# create directories under /work
#
sudo mkdir -p /work/runs
sudo mkdir -p /work/output
sudo mkdir -p /work/reports/catreport/reports
sudo mkdir -p /work/reports/resistanceapi/vcfs
sudo mkdir -p /work/logs/reports/resistanceapi
sudo mkdir -p /work/logs/fetchapi
sudo mkdir -p /work/logs/catweb

sudo chown $USERNAME -R /work/runs
sudo chown $USERNAME -R /work/output
sudo chown $USERNAME -R /work/reports/catreport/reports
sudo chown $USERNAME -R /work/reports/resistanceapi/vcfs
sudo chown $USERNAME -R /work/logs/reports/resistanceapi
sudo chown $USERNAME -R /work/logs/fetchapi
sudo chown $USERNAME -R /work/logs/catweb

#
# create database directory
#
sudo mkdir -p /db
sudo chown $USERNAME -R /db

#
# copy resistance data from repo
#
sudo cp -r $SP3PREFIX/resistance/piezo/config/* /data/reports/resistance/data
sudo cp -r $SP3PREFIX/resistance/data/* /data/reports/resistance/data

#
# copy example configs to main configs
#
cp $SP3PREFIX/instance.yaml-example $SP3PREFIX/instance.yaml
cp $SP3PREFIX/catweb/config.yaml-example $SP3PREFIX/catweb/config.yaml
cp $SP3PREFIX/catcloud/config.yaml-example $SP3PREFIX/catcloud/config.yaml
cp $SP3PREFIX/download-api/config.yaml-example $SP3PREFIX/download-api/config.yaml
cp $SP3PREFIX/fetch-api/fetch_api.yaml-example $SP3PREFIX/fetch-api/fetch_api.yaml

cat<<EOF

Example configuration was created. You need to edit it:

    $SP3PREFIX/instance.yaml
    $SP3PREFIX/catweb/config.yaml
    $SP3PREFIX/catcloud/config.yaml
    $SP3PREFIX/download-api/config.yaml
    $SP3PREFIX/fetch-api/config.yaml

You also need to copy $SP3PREFIX/sp3doc/nginx/sp3 to your nginx config and edit it

To use SP3, you need nextflow pipelines, container images and references files
These should go in

    /data/pipelines
    /data/images
    /data/references (reference genomes)
    /data/databases (other data files required by pipelines)

EOF

