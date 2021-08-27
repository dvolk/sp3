import json
import logging
import time
import uuid

from utils import *


def gcp_get_server_by_ip(server_ip):
    r = run(f"gcloud compute instances list --format json")
    for vm in json.loads(r):
        name = vm["name"]
        private_ips = vm["networkInterfaces"][0]["networkIP"]
        if server_ip in private_ips:
            return name


def gcp_create_vm(
    name, zone, image_family, image_project, machine_type, boot_disk_size
):
    ret = run(
        f"gcloud compute instances create {name} --format json --zone={zone} --image-family={image_family} --image-project={image_project} --machine-type={machine_type} --boot-disk-size={boot_disk_size}"
    )
    return json.loads(ret)


def gcp_create_node(
    zone, image_family, image_project, machine_type, boot_disk_size, setup_script
):
    node_uuid = "node-" + str(uuid.uuid4())
    node_js = gcp_create_vm(
        node_uuid, zone, image_family, image_project, machine_type, boot_disk_size
    )
    server_ip = node_js[0]["networkInterfaces"][0]["networkIP"]

    wait_until_server_booted(server_ip)
    run_script(server_ip, setup_script)

    return server_ip


def gcp_destroy_node(server_ip, zone):
    server_name = gcp_get_server_by_ip(server_ip)
    run(
        f"gcloud --quiet compute instances delete {server_name} --zone {zone} --delete-disks all"
    )


class GCPNodeController:
    def __init__(
        self,
        zone,
        image_family,
        image_project,
        machine_type,
        boot_disk_size,
        setup_script,
    ):
        self.zone = zone
        self.image_family = image_family
        self.image_project = image_project
        self.machine_type = machine_type
        self.boot_disk_size = boot_disk_size
        self.setup_script = setup_script
        self.support_destroy_all = False

    def create(self):
        return gcp_create_node(
            self.zone,
            self.image_family,
            self.image_project,
            self.machine_type,
            self.boot_disk_size,
            self.setup_script,
        )

    def destroy(self, server_ip):
        return gcp_destroy_node(server_ip, self.zone)
