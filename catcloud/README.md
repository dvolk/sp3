               _       _                 _
      ___ __ _| |_ ___| | ___  _   _  __| |
     / __/ _` | __/ __| |/ _ \| | | |/ _` |
    | (_| (_| | || (__| | (_) | |_| | (_| |
     \___\__,_|\__\___|_|\___/ \__,_|\__,_|

# A cluster scaler for humans

## Description

catcloud is a python application that performs cloud compute scaling

It has 4 elements:

- node controller - an interface to create and destroy vms on specific infrastructure

  supported:
    - OpenStack
    - Google Cloud Platform
    - AWS
    - Oracle Cloud
    - Azure

- scheduler - an interface to a cluster scheduler

  supported:
    - catgrid

- scaler - taking information from the scheduler, spawns vms using the node controller

  supported:
    - one by one scaler

- script - bash script run when the vm is created

## Requirements

- python **3.6+**
- requests

### OpenStack

- python-openstackclient

### Azure

- azure-cli (https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-apt?view=azure-cli-latest)

## Installation

    git clone https://gitlab.com/dvolk/catcloud
    cd catcloud
    pip install -r requirements.txt

## Test

1. Start catgrid without nodes. Follow link: http://gitlab.com/dvolk/hypergrid

2. Start catcloud with test profile:

        python3 main.py --profile test
        
The test profile only adds 1 node: localhost

3. Use curl to submit job to catgrid:

        curl -H "Content-Type: application/json" -X POST \
        -d '{"name": "test", "script": "your_script.sh", "mem": "1", "work_dir": "/tmp"}' \
        http://127.0.0.1:6000/submit

This will return the `job id`.

4. Check job output with curl:

        curl http://127.0.0.1:6000/output/<job_id>

## Setup

You have to log in to your infrastructure before running catcloud

### Azure

You have to create a service principal (a login that the program can use):

    az account show --query "{subscriptionId:id, tenantId:tenantId}"
    az account set --subscription="your subscription id"
    az ad sp create-for-rbac --role="Contributor"

and login with az:

    az login --service-principal -u <appId> -p <password> --tenant <tenant>
    
### GCP

login with gcloud:

    gcloud auth login

### OpenStack

Download the OpenStack RC file (Compute - API Access) and source it:

    source your-rc-file.sh

## Configuration

see `config.yaml-example`:

    profiles:
      - name: azure-catcloudtest

        node_controller: node_controllers.azure.AzureNodeController
        scheduler: schedulers.catgrid.CatgridScheduler
        scaler: scalers.onebyone.OneByOneScaler

        scheduler_params: {}

        scaler_params:
          min_nodes: 0
          max_nodes: 99

        node_controller_params:
          resource_group: catcloudtest
          instance_type: Standard_E8s_v3
          vm_image: UbuntuLTS
          setup_script: scripts/azure_node_setup.sh

      - name: openstack-cardiff

        node_controller: node_controllers.openstack_cardiff.OpenstackCardiffNodeController
        scheduler: schedulers.catgrid.CatgridScheduler
        scaler: scalers.onebyone.OneByOneScaler

        scheduler_params: {}

        scaler_params:
          min_nodes: 0
          max_nodes: 8

        node_controller_params:
          flavor: climb.group
          network_uuid: 895d68df-6cff-45a1-9399-c10109b8bfbd
          key_name: denis
          vol_size: 120
          vol_image: Ubuntu-18.04-20181216
          setup_script: scripts/os_node_setup_cardiff.sh

## Running

    python3 main.py --profile [profile_name]
