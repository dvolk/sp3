import json
import logging
import time
import uuid

from utils import *


def aws_get_server_by_ip(server_ip):
    r = run(f"aws ec2 describe-instances")
    for vm_ in json.loads(r)["Reservations"]:
        vm = vm_["Instances"][0]
        name = vm["InstanceId"]
        if not "PrivateIpAddress" in vm:
            continue
        private_ips = vm["PrivateIpAddress"]
        if server_ip in private_ips:
            return name


def aws_create_vm(image_id, instance_type, key_name, security_group_id, subnet_id):
    ret = run(
        f"aws ec2 run-instances --image-id {image_id} --count 1 --instance-type {instance_type} --key-name {key_name} --security-group-id {security_group_id} --subnet-id {subnet_id}"
    )
    return json.loads(ret)


def aws_create_node(
    image_id, instance_type, key_name, security_group_id, subnet_id, setup_script
):
    node_js = aws_create_vm(
        image_id, instance_type, key_name, security_group_id, subnet_id
    )
    server_ip = node_js["Instances"][0]["PrivateIpAddress"]

    wait_until_server_booted(server_ip)
    run_script(server_ip, setup_script)

    return server_ip


def aws_destroy_node(server_ip):
    server_name = aws_get_server_by_ip(server_ip)
    run(f"aws ec2 terminate-instances --instance-ids {server_name}")


class AWSNodeController:
    def __init__(
        self,
        image_id,
        instance_type,
        key_name,
        security_group_id,
        subnet_id,
        setup_script,
    ):
        self.image_id = image_id
        self.instance_type = instance_type
        self.key_name = key_name
        self.security_group_id = security_group_id
        self.subnet_id = subnet_id
        self.setup_script = setup_script
        self.support_destroy_all = False

    def create(self):
        return aws_create_node(
            self.image_id,
            self.instance_type,
            self.key_name,
            self.security_group_id,
            self.subnet_id,
            self.setup_script,
        )

    def destroy(self, server_ip):
        return aws_destroy_node(server_ip)
