#!/bin/bash

set -e
set -x

#
# Check if we're running the right OS
#
if [ "$(cat /etc/issue | head -c 12)" != "Ubuntu 18.04" ]; then
    echo "*** This installation script requires Ubuntu 18.04."
    exit 1
fi

cd /home/ubuntu/sp3/

SP3PREFIX=$(pwd)
USERNAME=$(whoami)

#
# ubuntu 18.04 package manager prerequisites
#
sudo apt update
sudo apt install etckeeper -y
sudo apt install build-essential python3-virtualenv python3-pip virtualenv openjdk-8-jre-headless openvpn libpython3-all-dev libmysqlclient-dev nginx tree emacs-nox tig sqlite3 elpa-magit elpa-jinja2-mode iotop bmon sl pwgen s3fs -y
sudo apt-get install mongodb-server=1:3.6.3-0ubuntu1.4 -y

#
# nextflow
#
wget https://github.com/nextflow-io/nextflow/releases/download/v20.10.0/nextflow-20.10.0-all -O nextflow
sudo mv nextflow /usr/bin
sudo chmod a+x /usr/bin/nextflow

#
# Install psutil and cerberus globally
#
pip3 install psutil
pip3 install cerberus
pip3 install argh

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
# N.B Installing setuptools<58 sp PyVCF can install correctly
pip3 install setuptools==58
pip3 install -r requirements.txt
pip3 install waitress pymongo==3.12.0 newick argh markdown2 sentry-sdk sentry-sdk[flask]

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
sudo mkdir -p /data/reports/resistance
sudo mkdir -p /data/fetch
sudo mkdir -p /data/inputs
sudo mkdir -p /data/inputs/uploads
sudo mkdir -p /data/inputs/users
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

# Add blank index.html to avoid indexing
sudo touch /work/output/index.html

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
# copy example configs to main configs
#
cp $SP3PREFIX/instance.yaml-example $SP3PREFIX/instance.yaml
cp $SP3PREFIX/catweb/config.yaml-example $SP3PREFIX/catweb/config.yaml
cp $SP3PREFIX/catcloud/config.yaml-example $SP3PREFIX/catcloud/config.yaml
cp $SP3PREFIX/download-api/config.yaml-example $SP3PREFIX/download-api/config.yaml
cp $SP3PREFIX/fetch-api/fetch_api.yaml-example $SP3PREFIX/fetch-api/fetch_api.yaml
cp $SP3PREFIX/cattag/config.yaml-example $SP3PREFIX/cattag/config.yaml

#
# copy sp3 nginx config to ...
#
sudo cp $SP3PREFIX/sp3doc/oracle-deploy/nginx/sp3 /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/sp3 /etc/nginx/sites-enabled/sp3
sudo rm /etc/nginx/sites-enabled/default

sudo systemctl restart nginx

mkdir -p /home/ubuntu/.config/systemd/user
cp $SP3PREFIX/sp3doc/systemd/*.service /home/ubuntu/.config/systemd/user
systemctl --user daemon-reload

echo "TERM=xterm-256color" >> /home/ubuntu/.bashrc
