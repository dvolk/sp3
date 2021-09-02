import json
import logging
import time
import uuid

from utils import *


def az_get_server_by_ip(server_ip, resource_group):
    r = run(f"az vm list-ip-addresses -g {resource_group}")
    for vm in json.loads(r):
        name = vm["virtualMachine"]["name"]
        private_ips = vm["virtualMachine"]["network"]["privateIpAddresses"]
        if server_ip in private_ips:
            return name


def az_get_disk_name(server_name, resource_group):
    r = run(f"az vm show -g {resource_group} -n {server_name}")
    r = json.loads(r)
    return r["storageProfile"]["osDisk"]["name"]


def az_create_vm(name, resource_group, image, instance_type):
    ret = run(
        f'az vm create -g {resource_group} --name {name} --size {instance_type} --image {image} --output json --public-ip-address ""'
    )
    return json.loads(ret)


def az_create_node(instance_type, resource_group, vm_image, setup_script):
    node_uuid = str(uuid.uuid4())
    node_js = az_create_vm(node_uuid, resource_group, vm_image, instance_type)
    server_ip = node_js["privateIpAddress"]

    wait_until_server_booted(server_ip)
    run_script(server_ip, setup_script)

    return server_ip


def az_destroy_node(server_ip, resource_group):
    server_name = az_get_server_by_ip(server_ip, resource_group)
    server_disk_name = az_get_disk_name(server_name, resource_group)

    run(f"az vm delete -g {resource_group} --name {server_name} --yes")
    run(f"az disk delete -g {resource_group} --name {server_disk_name} --yes")
    run(f"az network nic delete -g {resource_group} -n {server_name}VMNic")
    run(f"az network nsg delete -g {resource_group} -n {server_name}NSG")


class AzureNodeController:
    def __init__(self, instance_type, resource_group, vm_image, setup_script):
        self.instance_type = instance_type
        self.resource_group = resource_group
        self.vm_image = vm_image
        self.setup_script = setup_script
        self.support_destroy_all = False

    def create(self):
        return az_create_node(
            self.instance_type, self.resource_group, self.vm_image, self.setup_script
        )

    def destroy(self, server_ip):
        return az_destroy_node(server_ip, self.resource_group)
