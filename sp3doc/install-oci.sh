#! /bin/bash

###### catcloud
cd ../catcloud/
cp config.yaml-example config.yaml

# find out the OCIDs of the compartment and the subnet
COMP=$(curl -s http://169.254.169.254/opc/v1/instance/ | jq '.compartmentId')
SUBNET=$(curl -s http://169.254.169.254/opc/v1/instance/ | jq '.metadata.subnet_id')

# replace them in the yaml
sed -i 's/ocid1.compartment.oc1..aaaaaaaao4kpjckz2pjmlict2ssrnx45ims7ttvxghlluo2tcwv6pgfdlepq/'$COMP'/g' config.yaml
sed -i 's/ocid1.subnet.oc1.uk-london-1.aaaaaaaab3zsfqtkoyxtaogsp4bgzv4ofcfv7wzulehwiutxraanpcgasloa/'$SUBNET'/g' config.yaml

###### catweb

SUBDOMAIN=`cat ~/deployment_id`
cd ../catweb/
sed -i 's/192.168.9.9/10.0.1.2/g' config.yaml
sed -i 's/cats./'$SUBDOMAIN'/g' config.yaml


###### catdap
cd ../catdap/
cp config.yaml-oracle config.yaml


###### catpile
cd ../catpile
cp config.yaml-example config.yaml

###### cattag
cd ../cattag
sed -i 's/10.218.117.11/10.0.1.2/g' config.yaml


###### download
cd ../download-api/
sed -i 's/cats./'$SUBDOMAIN.'/g' config.yaml

###### fetch
cd ../fetch-api/
cp config.yaml-example config.yaml



