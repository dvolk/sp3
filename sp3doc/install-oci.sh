#! /bin/bash

set -x

sudo -s
echo '/work 10.0.1.2/255.255.255.0(rw,async,root_squash,crossmnt)' > /etc/exports
echo '/data 10.0.1.2/255.255.255.0(ro,async,root_squash,crossmnt)' > /etc/exports
systemctl restart nfs-server
exit

###### catcloud
cd /home/ubuntu/sp3/catcloud/
cp config.yaml-example config.yaml

# find out the OCIDs of the compartment and the subnet
COMP=$(curl -s http://169.254.169.254/opc/v1/instance/ | jq '.compartmentId')
SUBNET=$(curl -s http://169.254.169.254/opc/v1/instance/ | jq '.metadata.subnet_id')

# replace them in the yaml
sed -i 's/ocid1.compartment.oc1..aaaaaaaao4kpjckz2pjmlict2ssrnx45ims7ttvxghlluo2tcwv6pgfdlepq/'$COMP'/g' config.yaml
sed -i 's/ocid1.subnet.oc1.uk-london-1.aaaaaaaab3zsfqtkoyxtaogsp4bgzv4ofcfv7wzulehwiutxraanpcgasloa/'$SUBNET'/g' config.yaml

###### catweb

SUBDOMAIN=$(jq -r .deployment_id /home/ubuntu/stack_info.json)
cd /home/ubuntu/sp3/catweb/
cp config.yaml-example config.yaml
sed -i 's/192.168.9.9/10.0.1.2/g' config.yaml
sed -i 's/cats./'$SUBDOMAIN'/g' config.yaml

###### catdap
cd /home/ubuntu/sp3/catdap/
cp config.yaml-oracle config.yaml

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
sed -i 's/cats./'$SUBDOMAIN.'/g' config.yaml

###### fetch
cd /home/ubuntu/sp3/fetch-api/
cp fetch_api.yaml-example fetch_api.yaml

###### Start cats services
systemctl --user restart catdap
systemctl --user restart catdownload
systemctl --user restart catfetch
systemctl --user restart catgrid
systemctl --user restart catstat
systemctl --user restart cattag
systemctl --user restart catpile
systemctl --user restart catwebapi
systemctl --user restart catwebui
