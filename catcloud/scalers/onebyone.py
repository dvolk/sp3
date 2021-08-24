import logging
import time
import signal
import requests


class OneByOneScaler:
    def __init__(self, min_nodes, max_nodes):
        self.min_nodes, self.max_nodes = min_nodes, max_nodes
        self.run_scaler = True

    def init(self, scheduler, node_controller):
        self.node_controller = node_controller
        self.scheduler = scheduler

    def run(self):
        last_nodes_len = 0
        last_queue_len = 0
        while self.run_scaler:
            time.sleep(10)
            nodes_len, queue_len, idle_nodes = self.scheduler.get_info()
            if nodes_len != last_nodes_len or queue_len != last_queue_len:
                logging.warning(f"nodes: {nodes_len}, queue: {queue_len}")
                last_nodes_len = nodes_len
                last_queue_len = queue_len

            if (
                queue_len > 0 and nodes_len < self.max_nodes
            ) or nodes_len < self.min_nodes:
                logging.warning("creating new node")
                new_node_ip = self.node_controller.create()
                self.scheduler.add_node(new_node_ip)
                logging.warning(f"created new_node: {new_node_ip}")
                continue

            if nodes_len > self.min_nodes:
                if idle_nodes:
                    idle_node_ip = idle_nodes[0]
                    logging.warning(f"destroying idle node: {idle_node_ip}")
                    self.scheduler.remove_node(idle_node_ip)
                    self.node_controller.destroy(idle_node_ip)
                    logging.warning(f"destroyed node: {idle_node_ip}")
                    continue

    def stop(self):
        self.run_scaler = False
        r = requests.get("http://127.0.0.1:6000/status").json()
        nodes_running = r["nodes"]

        if self.node_controller.support_destroy_all:
            node_names = []
            for node_name, node in nodes_running.items():
                node_names.append(node_name)
                self.scheduler.remove_node(node_name)
            logging.warning(f"removed nodes f{node_names}")
            destroyed_nodes = self.node_controller.destroy_all()
            logging.warning(f"destroyed all nodes: { destroyed_nodes }")
        else:
            for node_name, node in nodes_running.items():
                self.scheduler.remove_node(node_name)
                self.node_controller.destroy(node_name)
                logging.warning(f"destroyed node: {node_name}")