import json

import argh
import yaml


def main(stack_info_filename, catcloud_config_filename):
    with open(stack_info_filename) as f:
        stack_info = json.loads(f.read())

    with open(catcloud_config_filename) as f:
        config = yaml.load(f)

    pos = 0
    for i, c in enumerate(config["profiles"]):
        if c["name"] == "oracle-test":
            pos = i
            break

    config["profiles"].remove(c)

    c["node_controller_params"]["compartment_id"] = stack_info["compartment_id"]
    c["node_controller_params"]["availability_domain"] = stack_info[
        "availability_domain"
    ]
    c["node_controller_params"]["image_id"] = stack_info["worker_node"]["worker_image"]
    c["node_controller_params"]["shape"] = stack_info["worker_node"]["worker_shape"]
    c["node_controller_params"]["subnet_id"] = stack_info["subnet_id"]
    c["scaler_params"]["min_nodes"] = stack_info["worker_node"]["worker_min"]
    c["scaler_params"]["max_nodes"] = stack_info["worker_node"]["worker_max"]

    config["profiles"].append(c)

    print(yaml.dump(config, default_flow_style=False))


if __name__ == "__main__":
    argh.dispatch_command(main)
