import json
import logging
import time
import uuid

from utils import *


def oracle_get_server_by_ip(server_ip, subnet_id):
    r = run(
        f"oci network private-ip list --subnet-id {subnet_id} --auth instance_principal"
    )
    for vm in json.loads(r)["data"]:
        if vm["ip-address"] == server_ip:
            return vm["display-name"]


def oracle_get_instance_id_from_name(display_name, compartment_id):
    vms = run(
        f"oci compute instance list -c { compartment_id } --auth instance_principal"
    )
    for vm in json.loads(vms)["data"]:
        if vm["display-name"] == display_name:
            return vm["id"]


def oracle_create_vm(
    name,
    compartment_id,
    availability_domain,
    image_id,
    shape,
    subnet_id,
    boot_volume_size_in_gbs,
):
    cmd = f"""
oci compute instance launch \
    -c { compartment_id } \
    --availability-domain { availability_domain } \
    --shape { shape } \
    --display-name { name } \
    --image-id { image_id } \
    --ssh-authorized-keys-file "/home/ubuntu/.ssh/id_rsa.pub" \
    --subnet-id { subnet_id } \
    --auth instance_principal \
    --boot-volume-size-in-gbs { boot_volume_size_in_gbs }"""
    # TODO: --assign-public-ip false

    ret = run(cmd)
    return json.loads(ret)


def oracle_get_ip_by_name(name, subnet_id):
    r = run(
        f"oci network private-ip list --subnet-id {subnet_id} --auth instance_principal"
    )
    for vm in json.loads(r)["data"]:
        if vm["display-name"] == name:
            return vm["ip-address"]


def oracle_create_node(
    compartment_id,
    availability_domain,
    image_id,
    shape,
    subnet_id,
    boot_volume_size_in_gbs,
    setup_script,
):
    node_uuid = str(uuid.uuid4())
    node_js = oracle_create_vm(
        node_uuid,
        compartment_id,
        availability_domain,
        image_id,
        shape,
        subnet_id,
        boot_volume_size_in_gbs,
    )

    while True:
        server_ip = oracle_get_ip_by_name(node_uuid, subnet_id)
        if server_ip:
            break
        time.sleep(10)

    wait_until_server_booted(server_ip)
    run_script(server_ip, setup_script)

    return server_ip


def oracle_destroy_node(server_ip, subnet_id, compartment_id):
    server_name = oracle_get_server_by_ip(server_ip, subnet_id)
    instance_id = oracle_get_instance_id_from_name(server_name, compartment_id)
    run(
        f"oci compute instance terminate --force --instance-id { instance_id } --preserve-boot-volume false --auth instance_principal"
    )


class OracleNodeController:
    def __init__(
        self,
        compartment_id,
        availability_domain,
        image_id,
        shape,
        subnet_id,
        boot_volume_size_in_gbs,
        setup_script,
    ):
        self.compartment_id = compartment_id
        self.availability_domain = availability_domain
        self.shape = shape
        self.image_id = image_id
        self.subnet_id = subnet_id
        self.boot_volume_size_in_gbs = boot_volume_size_in_gbs
        self.setup_script = setup_script
        self.support_destroy_all = False

    def create(self):
        return oracle_create_node(
            self.compartment_id,
            self.availability_domain,
            self.image_id,
            self.shape,
            self.subnet_id,
            self.boot_volume_size_in_gbs,
            self.setup_script,
        )

    def destroy(self, server_ip):
        return oracle_destroy_node(server_ip, self.subnet_id, self.compartment_id)
