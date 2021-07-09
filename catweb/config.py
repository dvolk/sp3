import datetime
import glob
import logging
import os
import pathlib
import shlex
import subprocess

import yaml

import validate


class Config:
    """
    Configuration parsed directly from a YAML file
    """

    def __init__(self):
        self.config = None

    def git_last_commit(self, directory):
        """
        get the time of the last commit
        """
        old = os.getcwd()
        os.chdir(directory)
        cmd = "git log -1 --format=%ct"
        last_commit = subprocess.check_output(shlex.split(cmd)).decode("utf-8").strip()
        os.chdir(old)
        return last_commit

    def git_describe(self, directory):
        """
        get the git version of the repo
        """
        old = os.getcwd()
        os.chdir(directory)
        cmd = "git describe --tags --always --dirty"
        version = subprocess.check_output(shlex.split(cmd)).decode("utf-8").strip()

        # style fix: remove possible leading v from version
        if version[0] == "v":
            version = version[1:]
        os.chdir(old)
        return version

    def load(self, config_file):
        # validate config.yaml with config.yaml.schema
        with open(config_file, "r") as stream:
            ok, errs = validate.validate_yaml("config.yaml.schema", config_file)
            if ok:
                logging.warning(f"{config_file} validated")
            else:
                logging.warning(f"{config_file} validation failed")
                logging.warning(str(errs))

            self.config = yaml.load(stream)

        if "canonical_prog_dir" not in self.config:
            return

        # add catweb git version to config
        self.config["catweb_version"] = self.git_describe(".")
        logging.warning(f"catweb version: {self.config['catweb_version']}")

        # load nextflow pipeline files
        self.config["nextflows"] = list()
        for filename in pathlib.Path("config.yaml.d/orgs/").glob("**/*.yaml"):
            logging.warning(f"loading {filename}")
            with open(filename) as f:
                cfg = yaml.load(f.read())
            org_containing_dir = pathlib.Path(filename).parent.stem
            cfg["filepath"] = str(filename)
            cfg["organisation"] = org_containing_dir
            # prefix nextflow name with organisation
            cfg["name"] = org_containing_dir + "-" + cfg["name"]
            self.config["nextflows"].append(cfg)

        for nextflow in self.get("nextflows"):
            # construct the path to the git repo (presumably) containing the nextflow file
            new = str(
                pathlib.Path(self.config["canonical_prog_dir"]) / nextflow["prog_dir"]
            )

            nextflow["last_commit"] = self.git_last_commit(new)
            nextflow["git_version"] = self.git_describe(new)
            last_commit_pretty = datetime.datetime.fromtimestamp(
                int(nextflow["last_commit"])
            ).strftime("%F %T")
            nextflow["last_commit_pretty"] = last_commit_pretty
            nextflow[
                "version"
            ] = f"Version: {last_commit_pretty} Last commit: {nextflow['git_version']}"

            print(f"{new} {nextflow['version']}")

            # for params with switch type, scan the globs array,
            # glob the directories and add them to the options
            for p in nextflow["param"]["description"]:
                if "type" in p and p["type"] == "switch":
                    if "options" not in p:
                        p["options"] = dict()
                    for fglob in p.get("globs", list()):
                        files = glob.glob(fglob)
                        for f in files:
                            p["options"][f] = f

    def load_str(self, config_str: str):
        self.config = yaml.load(config_str)

    def get(self, field: str):
        return self.config.get(field)
