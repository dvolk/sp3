          ___           ___           ___           ___           ___
         /\__\         /\  \         /\__\         /\  \         /\  \
        /::|  |       /::\  \       /:/ _/_       /::\  \       /::\  \
       /:|:|  |      /:/\:\  \     /:/ /\__\     /:/\:\  \     /:/\:\  \
      /:/|:|  |__   /::\~\:\  \   /:/ /:/ _/_   /::\~\:\  \   /::\~\:\__\
     /:/ |:| /\__\ /:/\:\ \:\__\ /:/_/:/ /\__\ /:/\:\ \:\__\ /:/\:\ \:|__|
     \/__|:|/:/  / \/__\:\ \/__/ \:\/:/ /:/  / \:\~\:\ \/__/ \:\~\:\/:/  /
         |:/:/  /       \:\__\    \::/_/:/  /   \:\ \:\__\    \:\ \::/  /
         |::/  /         \/__/     \:\/:/  /     \:\ \/__/     \:\/:/  /
         /:/  /                     \::/  /       \:\__\        \::/__/
         \/__/                       \/__/         \/__/         ~~

# nfweb

## Requirements

- python **3.6+**
- python libraries: pandas, requests, flask, flask_login, yaml, ldap3, passlib,
cerberus
- nextflow
- SLURM

## Installation

    git clone https://github.com/dvolk/nfweb
    cd nfweb
    virtualenv -p python3.6 env
    source env/bin/activate
    pip3 install -r requirements.txt

## Configure

nfweb is configured by editing config.yaml

It comes with an example configuration file in config.yaml-example. Copy it to
config.yaml and edit it to your specifications.

The individual pipeline configuration can be in its own files, and then
included in the main config with the '!include' command. See config.yaml-example
for examples of this
