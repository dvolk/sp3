import logging
import time

class OneByOneScaler:
    def __init__(self, min_nodes, max_nodes):
        self.min_nodes, self.max_nodes = min_nodes, max_nodes

    def init(self, scheduler, node_controller):
        self.node_controller = node_controller
        self.scheduler = scheduler

    def run(self):
        while True:
            time.sleep(10)
            nodes_len, queue_len, idle_nodes = self.scheduler.get_info()
            logging.warning(f'nodes: {nodes_len}, queue: {queue_len}')

            if (queue_len > 0 and nodes_len < self.max_nodes) or nodes_len < self.min_nodes:
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
