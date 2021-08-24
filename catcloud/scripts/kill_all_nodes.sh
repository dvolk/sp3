#/bin/bash
source /home/ubuntu/.profile 
export OCI_CLI_AUTH=instance_principal 
systemctl --user stop catcloud-oracle.service
cd /home/ubuntu/sp3/catcloud 
/home/ubuntu/env/bin/python /home/ubuntu/sp3/catcloud/kill_all_nodes.py --profile oracle-test