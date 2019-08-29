# persistence

## Description

Persistence consists of a program that syncs files from a cloud instance to the persistent store (sync.py) and a web interface to the persistent store (ui.py)

## Requirements

- Python 3.6+
- pyyaml
- flask
- requests

## Installation

    git clone https://gitlab.com/MMMCloudPipeline/persistence
    cd persistence
    pip3 install -r requirements.txt

## Adding a new instance

On the instance head node, create a configuration file ~/sp3/instance.yaml. e.g.:

    name: Cats
    id: 44444444-4444-4444-4444-444444444444
    store: 131.251.130.111
    url: https://cats.oxfordfun.com
    contact: denis.volk@ndm.ox.ac.uk
    description: SP3 instance in CLIMB Cardiff

You MUST generate a new ID (with e.g. uuidgen)

Add the instance public ssh key to the persistent store

Run sync.py on the instance head to sync to the persistent store