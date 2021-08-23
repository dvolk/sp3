import json
import logging
import sys
import time
import uuid

from utils import *


def os_create_volume(name, size, image):
    out = run(f"openstack volume create --size {size} --image {image} {name} -f json")
    return json.loads(out)


def os_get_volume(vol_uuid):
    out = run(f"openstack volume show {vol_uuid} -f json")
    return json.loads(out)


def os_create_server(name, flavor, network_uuid, key_name, vol_uuid):
    out = run(
        f"openstack server create --volume {vol_uuid} --flavor {flavor} --key-name {key_name} --nic net-id={network_uuid} {name} -f json"
    )
    return json.loads(out)


def os_get_server(server_uuid):
    out = run(f"openstack server show {server_uuid} -f json")
    return json.loads(out)


def os_get_server_ip(server_uuid):
    js = os_get_server(server_uuid)
    for p in js["addresses"].split("; "):
        net, ip = p.split("=")
        return ip


def os_get_server_volumes(server_uuid):
    js = os_get_server(server_uuid)
    ret = []
    for p in js["volumes_attached"].split("\n"):
        _, vol_uuid = p.split("=")
        ret.append(vol_uuid)
    return ret


def os_get_server_uuid_by_ip(server_ip):
    js = run(f"openstack server list -f json")
    for server in json.loads(js):
        for p in server["Networks"].split("; "):
            net, ip = p.split("=")
            if ip == server_ip:
                return server


def os_wait_until_volume_available(vol_uuid):
    while True:
        time.sleep(5)
        v = os_get_volume(vol_uuid)
        if v["status"] == "available":
            return v


def os_wait_until_server_active(server_uuid):
    while True:
        time.sleep(5)
        s = os_get_server(server_uuid)
        if s["status"] == "ACTIVE":
            return s


def os_make_node(vol_size, vol_image, key_name, flavor, network_uuid, setup_script):
    name = str(uuid.uuid4())
    vol_name = name + "-bootvol"

    v = os_create_volume(vol_name, vol_size, vol_image)
    vol_uuid = v["id"]
    os_wait_until_volume_available(vol_uuid)

    s = os_create_server(name, flavor, network_uuid, key_name, vol_uuid)
    server_uuid = s["id"]
    os_wait_until_server_active(server_uuid)
    server_ip = os_get_server_ip(server_uuid)
    wait_until_server_booted(server_ip)

    run_script(server_ip, setup_script)

    return server_ip


def os_destroy_node(server_ip):
    server = os_get_server_uuid_by_ip(server_ip)
    server_name = server["Name"]
    server_uuid = server["ID"]
    vol_uuids = os_get_server_volumes(server_uuid)

    # delete server
    run(f"openstack server delete {server_uuid}")
    while True:
        try:
            time.sleep(5)
            os_get_server(server_uuid)
        except:
            break

    # delete all volumes that were attached to server
    for vol_uuid in vol_uuids:
        run(f"openstack volume delete {vol_uuid}")
        while True:
            try:
                time.sleep(5)
                os_get_volume(f"{vol_uuid}")
            except:
                break


class OpenstackEBINodeController:
    def __init__(
        self, flavor, network_uuid, key_name, vol_size, vol_image, setup_script
    ):
        self.flavor = flavor
        self.network_uuid = network_uuid
        self.key_name = key_name
        self.vol_size = vol_size
        self.vol_image = vol_image
        self.setup_script = setup_script
        self.support_destroy_all = False

    def create(self):
        server_ip = os_make_node(
            self.vol_size,
            self.vol_image,
            self.key_name,
            self.flavor,
            self.network_uuid,
            self.setup_script,
        )
        return server_ip

    def destroy(self, server_ip):
        ret = os_destroy_node(server_ip)
        return ret


if __name__ == "__main__":
    main()
