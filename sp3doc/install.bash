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
sudo apt install build-essential python3-virtualenv python3-pip virtualenv openjdk-8-jre-headless openvpn libpython3-all-dev libmysqlclient-dev nginx tree emacs-nox tig 

#
# nextflow
#
wget https://github.com/nextflow-io/nextflow/releases/download/v18.10.1/nextflow-18.10.1-all -O nextflow
sudo mv nextflow /usr/bin
sudo chmod a+x /usr/bin/nextflow

#
# Install psutil and cerberus globally
#
pip3 install psutil
pip3 install cerberus

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
sudo mkdir -p /data/references/clockwork
sudo mkdir -p /data/reports/resistance/data
sudo mkdir -p /data/fetch
sudo mkdir -p /data/inputs
sudo mkdir -p /data/inputs/uploads
sudo mkdir -p /data/databases
sudo mkdir -p /data/databases/clockworkcloud
sudo mkdir -p /data/databases/clockworkcloud/kraken2

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
sudo cp -r $SP3PREFIX/resistance/resistanceapi/data/* /data/reports/resistance/data

#
# copy example configs to main configs
#
cp $SP3PREFIX/instance.yaml-example $SP3PREFIX/instance.yaml
cp $SP3PREFIX/catweb/config.yaml-example $SP3PREFIX/catweb/config.yaml
cp $SP3PREFIX/catcloud/config.yaml-example $SP3PREFIX/catcloud/config.yaml
cp $SP3PREFIX/download-api/config.yaml-example $SP3PREFIX/download-api/config.yaml
cp $SP3PREFIX/fetch-api/fetch_api.yaml-example $SP3PREFIX/fetch-api/fetch_api.yaml

#
# copy sp3 nginx config to ...
#
sudo cp $SP3PREFIX/sp3doc/nginx/sp3 /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/sp3 /etc/nginx/sites-enabled/sp3
sudo rm /etc/nginx/sites-enabled/default

#
# Download clockworkcloud pipeline
#
sudo git clone https://gitlab.com/MMMCloudPipeline/clockworkcloud /data/pipelines/clockworkcloud

sudo wget 'https://files.mmmoxford.uk/d/dd25a4cc6a424506a785/files/?p=/clockwork_container-0.7.7.img&dl=1' -O /data/images/clockwork_container-0.7.7.img
sudo wget 'https://files.mmmoxford.uk/d/dd25a4cc6a424506a785/files/?p=/fatos-1.7.img&dl=1' -O /data/images/fatos-1.7.img
sudo wget 'https://files.mmmoxford.uk/d/dd25a4cc6a424506a785/files/?p=/qc_vc.tar&dl=1' -O /data/references/clockwork/qc_vc.tar
sudo wget 'https://files.mmmoxford.uk/d/dd25a4cc6a424506a785/files/?p=/spectest4.tar&dl=1' -O /data/inputs/uploads/spectest4.tar

sudo wget 'ftp://ftp.ccb.jhu.edu/pub/data/kraken2_dbs/minikraken2_v2_8GB_201904_UPDATE.tgz' -O /data/databases/clockworkcloud/kraken2/minikraken2_v2_8GB_201904_UPDATE.tgz
sudo tar xf /data/databases/clockworkcloud/kraken2/minikraken2_v2_8GB_201904_UPDATE.tgz -C /data/databases/clockworkcloud/kraken2

sudo tar xf /data/references/clockwork/qc_vc.tar -C /data/references/clockwork
sudo tar xf /data/inputs/uploads/spectest4.tar -C /data/inputs/uploads

sudo rm /data/references/clockwork/qc_vc.tar
sudo rm /data/inputs/uploads/spectest4.tar

sudo rm /data/databases/clockworkcloud/kraken2/minikraken2_v2_8GB_201904_UPDATE.tgz

mkdir -p ~/.config/systemd/user
cp $SP3PREFIX/sp3doc/systemd/*.service ~/.config/systemd/user
systemctl --user daemon-reload

cat<<EOF

You need to create (sub)domains for
- Main instance interface (e.g.: cats.oxfordfun.com)
- File server (e.g.: download-cats.oxfordfun.com)
- Stats image (e.g.: stat-cats.oxfordfun.com)
- optional: Persistent store (e.g.: persistence.mmmoxford.uk)
- optional: Persistence file server (e.g.: persistent-files.mmmoxford.uk)
- optional: Labkey (e.g.: labkey.oxfordfun.com)

You need to edit /etc/nginx/sites-enabled/sp3 and change it to your domains

Example configuration was created. You need to edit it:

    $SP3PREFIX/instance.yaml
    $SP3PREFIX/catweb/config.yaml
    $SP3PREFIX/catcloud/config.yaml
    $SP3PREFIX/download-api/config.yaml
    $SP3PREFIX/fetch-api/fetch_api.yaml

To use SP3, you need nextflow pipelines, container images and references files
These should go in

    /data/pipelines
    /data/images
    /data/references (reference genomes)
    /data/databases (other data files required by pipelines)

EOF
