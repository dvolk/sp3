import yaml

config = None

with open("fetch_api.yaml") as h:
    config = yaml.load(h.read())
