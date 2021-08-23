import json
import logging
import time
import uuid

from utils import *


def test_create_node(setup_script):
    return "127.0.0.1"


def test_destroy_node(server_ip):
    pass


class TestNodeController:
    def __init__(self, setup_script):
        self.setup_script = setup_script
        self.support_destroy_all = False

    def create(self):
        return test_create_node(self.setup_script)

    def destroy(self, server_ip):
        return test_destroy_node(server_ip)
