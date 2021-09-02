import argparse
import importlib
import json
import logging
import os
import threading
import time
import uuid

import config
import utils

"""
Program to kill all nodes in the current OCI stack
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()

    cfg = config.Config()
    cfg.load("config.yaml")
    c = cfg.get_profile(args.profile)

    scheduler = utils.get_class_from_string(c["scheduler"])(**c["scheduler_params"])
    node_controller = utils.get_class_from_string(c["node_controller"])(
        **c["node_controller_params"]
    )
    scaler = utils.get_class_from_string(c["scaler"])(**c["scaler_params"])

    scaler.init(scheduler=scheduler, node_controller=node_controller)

    scaler.stop()

if __name__ == "__main__":
    main()