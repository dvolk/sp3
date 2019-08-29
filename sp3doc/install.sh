set -e

#
# Get install directory from user
#
SP3DIR=$HOME
echo -n "*** Where to install sp3? [Press return to use $SP3DIR] "
read answer
if [ "$answer" ]; then
    SP3DIR=$answer
fi

SP3PREFIX=$SP3DIR/sp3
USERNAME=`whoami`
cd $SP3DIR


#
# ubuntu 18.04 package manager prerequisites
#
sudo apt update
sudo apt install etckeeper
sudo apt install build-essential python3-virtualenv virtualenv openjdk-8-jre-headless openvpn
# libpython3-all-dev ??

#
# nextflow
#
wget https://github.com/nextflow-io/nextflow/releases/download/v18.10.1/nextflow-18.10.1-all -O nextflow
sudo mv nextflow /usr/bin
sudo chmod a+x /usr/bin/nextflow

#
# python virtualenv
#
virtualenv -p python3 env
source env/bin/activate

#
# sp3 packages
#
git clone https://gitlab.com/dvolk/sp3
cd sp3
pip3 install -r requirements.txt

#
# copy slurm emu files to /usr/bin
#
sudo cp $SP3PREFIX/catgrid/tools/slurm_emu/* /usr/bin
sudo chmod a+x /usr/bin/{sbatch,squeue,scancel}

sudo mkdir -p /data/images
sudo mkdir -p /data/pipelines
sudo mkdir -p /data/references
sudo mkdir -p /data/reports/resistance/data
sudo mkdir -p /data/fetch
sudo mkdir -p /data/inputs

sudo chown $USERNAME /data/fetch
sudo chown $USERNAME /data/inputs

sudo mkdir -p /work/runs
sudo mkdir -p /work/output
sudo mkdir -p /work/reports/catreport/reports
sudo mkdir -p /work/reports/resistanceapi/vcfs
sudo mkdir -p /work/logs/reports/resistanceapi
sudo mkdir -p /work/logs/fetchapi
sudo mkdir -p /work/logs/catweb

sudo mkdir -p /db
sudo chown $USERNAME /db

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

EOF

