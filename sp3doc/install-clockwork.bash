SP3PREFIX=/home/ubuntu/sp3

pip3 install pysam ujson

#
# resistance packages
#
cd $SP3PREFIX/resistance/gumpy
pip3 install .
cd $SP3PREFIX/resistance/piezo
pip3 install .

#
# download resistance data
#
sudo wget 'https://files.mmmoxford.uk/f/2b0ec8714da74e74b439/?dl=1' -O /data/reports/resistance-data-20200222.tgz
sudo tar xf /data/reports/resistance-data-20200222.tgz -C /data/reports/
sudo rm /data/reports/resistance-data-20200222.tgz

#
# Download clockworkcloud pipeline
#
sudo git clone https://gitlab.com/MMMCloudPipeline/clockworkcloud /data/pipelines/clockworkcloud

sudo wget 'https://files.mmmoxford.uk/f/1db2f26b8cc94b159410/?dl=1' -O /data/images/mykrobe_v0.9.0.img
sudo wget 'https://files.mmmoxford.uk/f/8717bc60c7f94851ad1b/?dl=1' -O /data/images/clockwork_container_20210222.img
sudo wget 'https://files.mmmoxford.uk/f/185b1c33b4b34c55a645/?dl=1' -O /data/images/fatos-20210205T144030_3.1.img
sudo wget 'https://files.mmmoxford.uk/f/3b2f62aa66184301bf44/?dl=1' -O /data/images/oxfordmmm_compasscompact_v1.0.3.img

sudo wget 'https://files.mmmoxford.uk/d/dd25a4cc6a424506a785/files/?p=/qc_vc.tar&dl=1' -O /data/references/clockwork/qc_vc.tar
sudo wget 'https://files.mmmoxford.uk/d/dd25a4cc6a424506a785/files/?p=/spectest4.tar&dl=1' -O /data/inputs/uploads/spectest4.tar

sudo wget 'ftp://ftp.ccb.jhu.edu/pub/data/kraken2_dbs/minikraken_8GB_202003.tgz' -O /data/databases/clockworkcloud/kraken2/minikraken2.tgz
sudo tar xf /data/databases/clockworkcloud/kraken2/minikraken2.tgz -C /data/databases/clockworkcloud/kraken2

sudo tar xf /data/references/clockwork/qc_vc.tar -C /data/references/clockwork
sudo tar xf /data/inputs/uploads/spectest4.tar -C /data/inputs/uploads

sudo rm /data/references/clockwork/qc_vc.tar
sudo rm /data/inputs/uploads/spectest4.tar

sudo rm /data/databases/clockworkcloud/kraken2/minikraken2.tgz
