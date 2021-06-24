import logging
import time

import requests


class CatgridScheduler:
    def __init__(self, node_timeout=300):
        # time elapsed since last job after which a node will be marked as
        # idle (and probably terminated)
        self.node_timeout = node_timeout

    def get_info(self):
        r = requests.get("http://127.0.0.1:6000/status").json()

        nodes_running = r["nodes"]
        queue = r["queue"]

        # get idle nodes
        idle_nodes = list()
        time_now = int(time.time())

        for node_name, node in nodes_running.items():
            if (
                not node["jobs"]
                and time_now - node["last_finished"] > self.node_timeout
            ):
                idle_nodes.append(node_name)

        return len(nodes_running), len(queue), idle_nodes

    def add_node(self, node_name):
        r = requests.get(f"http://127.0.0.1:6000/add_node/{node_name}")

    def remove_node(self, node_name):
        r = requests.get(f"http://127.0.0.1:6000/remove_node/{node_name}")
