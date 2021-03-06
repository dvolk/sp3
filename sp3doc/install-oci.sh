#! /bin/bash

set -x


echo '/work 10.0.1.2/255.255.255.0(rw,async,root_squash,crossmnt)' | sudo tee -a /etc/exports
echo '/data 10.0.1.2/255.255.255.0(rw,async,root_squash,crossmnt)' | sudo tee -a /etc/exports
sudo systemctl restart nfs-server


###### catweb

SP3URL=$(jq -r .sp3_url /home/ubuntu/stack_info.json)
cd /home/ubuntu/sp3/catweb/
cp config.yaml-example config.yaml
sed -i 's/192.168.9.9/10.0.1.2/g' config.yaml
sed -i 's;https://cats.oxfordfun.com;'$SP3URL';g' config.yaml
python3 make_secret_key.py

# configure covid pipeline
cd /home/ubuntu/sp3/catweb/config.yaml.d
mkdir -p orgs/oxforduni
cd orgs/oxforduni
ln -s /home/ubuntu/sp3/catweb/config.yaml.d/all/ncov2019-artic-illumina.yaml
ln -s /home/ubuntu/sp3/catweb/config.yaml.d/all/ncov2019-artic-nanopore.yaml
ln -s /home/ubuntu/sp3/catweb/config.yaml.d/all/ncov2019-artic-analysis.yaml
cd /data/pipelines/
sudo git clone https://github.com/oxfordmmm/ncov2019-artic-nf
cd /data/pipelines/ncov2019-artic-nf
NCOV_ARTIC_ENV=$(git tag -l --sort=-v:refname "sp3env-v*"| head -n 1)
if [ "${NCOV_ARTIC_ENV}" != "" ]
then
    sudo git checkout ${NCOV_ARTIC_ENV}
fi

###### catdap
cd /home/ubuntu/sp3/catdap/
cp config.yaml-oracle config.yaml
source /home/ubuntu/env/bin/activate
python3 convert.py
python3 catdap-cli.py reset-pw admin > admin-pw-delete-me
deactivate

###### catpile
cd /home/ubuntu/sp3/catpile/
cp config.yaml-example config.yaml

###### cattag
cd /home/ubuntu/sp3/cattag/
cp config.yaml-example config.yaml
sed -i 's/10.218.117.11/10.0.1.2/g' config.yaml

###### download
cd /home/ubuntu/sp3/download-api/
cp config.yaml-example config.yaml
sed -i 's;https://cats.oxfordfun.com;'$SP3URL';g' config.yaml

###### fetch
cd /home/ubuntu/sp3/fetch-api/
cp fetch_api.yaml-example fetch_api.yaml

###### Start cats services

# don't kill services when last session quits
loginctl enable-linger ubuntu

systemctl --user restart catdap
systemctl --user restart catdownload
systemctl --user restart catfetch
systemctl --user restart catgrid
systemctl --user restart catstat
systemctl --user restart cattag
systemctl --user restart catpile
systemctl --user restart catweb

systemctl --user enable catdap catdownload catfetch catgrid catstat cattag catpile catweb

sleep 60

###### catcloud
ssh-keygen -b 2048 -t rsa -f /home/ubuntu/.ssh/id_rsa -q -N ""

source /home/ubuntu/env/bin/activate
pip3 install argh
python3 /home/ubuntu/sp3/sp3doc/oracle-deploy/configure_catcloud.py /home/ubuntu/stack_info.json /home/ubuntu/sp3/catcloud/config.yaml-example > /home/ubuntu/sp3/catcloud/config.yaml

systemctl --user restart catcloud-oracle

sleep 5

###### catsgo
cd /home/ubuntu
git clone https://github.com/oxfordmmm/catsgo
cd catsgo
CATSGO_VERSION=$(git tag -l --sort=-v:refname "v*" | head -n 1)
if [ "${CATSGO_VERSION}" != "" ]
then
    git checkout ${CATSGO_VERSION}
fi
cp config.json-covid config.json
sed -i 's/test_user/admin/g' config.json
ADMIN_PWD=$(cat /home/ubuntu/sp3/catdap/admin-pw-delete-me)
sed -i 's/test_password/'$ADMIN_PWD'/g' config.json
SP3_URL=$(jq -r '.sp3_url' /home/ubuntu/stack_info.json)
sed -i 's#sp3_covid_site#'$SP3_URL'#g' config.json

source /home/ubuntu/env/bin/activate
pip3 install -r requirements.txt
#python3 catsgo.py run-covid-illumina "oxforduni-ncov2019-artic-nf-illumina" "/data/inputs/uploads/oxforduni/210204_M01746_0015_000000000-JHB5M"
