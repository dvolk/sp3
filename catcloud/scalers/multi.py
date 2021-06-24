import logging
import threading
import time


class MultiScaler:
    # creates nodes in groups of size max_creating_nodes
    # waits until group is created before checking queue again
    def __init__(self, min_nodes, max_nodes, cpus_per_node, max_creating_nodes):
        self.min_nodes, self.max_nodes = min_nodes, max_nodes
        self.cpus_per_node = cpus_per_node
        self.max_creating_nodes = max_creating_nodes

    def init(self, scheduler, node_controller):
        self.node_controller = node_controller
        self.scheduler = scheduler

    def new_node(self):
        logging.warning("creating new node")
        new_node_ip = self.node_controller.create()
        self.scheduler.add_node(new_node_ip)
        logging.warning(f"created new_node: {new_node_ip}")

    def create_a_bunch_of_nodes(self, n_nodes_to_add):
        Ts = [threading.Thread(target=self.new_node) for _ in range(n_nodes_to_add)]
        for T in Ts:
            T.start()
        for T in Ts:
            T.join()

    def run(self):
        last_nodes_len = 0
        last_queue_len = 0

        while True:
            time.sleep(10)
            nodes_len, queue_len, idle_nodes = self.scheduler.get_info()

            if nodes_len != last_nodes_len or queue_len != last_queue_len:
                logging.warning(f"nodes: {nodes_len}, queue: {queue_len}")
                last_nodes_len = nodes_len
                last_queue_len = queue_len

            # how many nodes min_nodes demands
            a = self.min_nodes - nodes_len
            # how many the queue demands
            b = queue_len // self.cpus_per_node
            # max nodes that can be created
            c = self.max_nodes - nodes_len
            d = min(b, c)  # max nodes to add

            n_nodes_to_add = max(a, d)

            # debug
            # logging.warning(f"self.min_nodes={self.min_nodes}, nodes_len={nodes_len}, queue_len={queue_len}, self.cpus_per_node={self.cpus_per_node}, self.max_nodes={self.max_nodes}, nodes_len={nodes_len}, n_nodes_to_add={n_nodes_to_add}, a={a}, b={b}, c={c}, d={d}")

            if n_nodes_to_add > 0:
                if self.max_creating_nodes:
                    n_nodes_to_add = min(self.max_creating_nodes, n_nodes_to_add)
                logging.warning(f"making {n_nodes_to_add} nodes")
                self.create_a_bunch_of_nodes(n_nodes_to_add)

            if nodes_len > self.min_nodes:
                if idle_nodes:
                    idle_node_ip = idle_nodes[0]
                    logging.warning(f"destroying idle node: {idle_node_ip}")
                    self.scheduler.remove_node(idle_node_ip)
                    self.node_controller.destroy(idle_node_ip)
                    logging.warning(f"destroyed node: {idle_node_ip}")
                    continue


class FastMultiScaler:
    # creates nodes in groups of size max_creating_nodes
    # doesn't wait for group to be created to check queue again
    def __init__(self, min_nodes, max_nodes, cpus_per_node=4):
        self.min_nodes, self.max_nodes = min_nodes, max_nodes
        self.cpus_per_node = cpus_per_node
        self.creating_nodes_count = 0

    def init(self, scheduler, node_controller):
        self.node_controller = node_controller
        self.scheduler = scheduler

    def new_node(self):
        logging.warning("creating new node")
        new_node_ip = self.node_controller.create()
        self.scheduler.add_node(new_node_ip)
        logging.warning(f"created new_node: {new_node_ip}")
        self.creating_nodes_count -= 1

    def create_a_bunch_of_nodes(self, n_nodes_to_add):
        Ts = [
            threading.Thread(target=self.new_node).start()
            for _ in range(n_nodes_to_add)
        ]

    def run(self):
        last_nodes_len = 0
        last_queue_len = 0

        while True:
            time.sleep(10)
            nodes_len, queue_len, idle_nodes = self.scheduler.get_info()

            if nodes_len != last_nodes_len or queue_len != last_queue_len:
                logging.warning(f"nodes: {nodes_len}, queue: {queue_len}")
                last_nodes_len = nodes_len
                last_queue_len = queue_len

            # how many nodes min_nodes demands
            a = self.min_nodes - nodes_len
            # how many the queue demands
            b = queue_len // self.cpus_per_node
            # max nodes that can be created
            c = self.max_nodes - nodes_len - self.creating_nodes_count
            d = min(b, c)

            n_nodes_to_add = max(a, d)

            # debug
            logging.warning(
                f"self.min_nodes={self.min_nodes}, nodes_len={nodes_len}, queue_len={queue_len}, self.cpus_per_node={self.cpus_per_node}, self.max_nodes={self.max_nodes}, nodes_len={nodes_len}, n_nodes_to_add={n_nodes_to_add}, a={a}, b={b}, c={c}, d={d}, self.creating_nodes_count={self.creating_nodes_count}"
            )

            if n_nodes_to_add > 0:
                self.creating_nodes_count += n_nodes_to_add
                self.create_a_bunch_of_nodes(n_nodes_to_add)

            if nodes_len > self.min_nodes:
                if idle_nodes:
                    idle_node_ip = idle_nodes[0]
                    logging.warning(f"destroying idle node: {idle_node_ip}")
                    self.scheduler.remove_node(idle_node_ip)
                    self.node_controller.destroy(idle_node_ip)
                    logging.warning(f"destroyed node: {idle_node_ip}")
                    continue
