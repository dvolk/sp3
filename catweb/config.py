import os
import subprocess
import pathlib
import shlex
import datetime
import glob

import yaml

import validate

# https://stackoverflow.com/questions/528281/how-can-i-include-a-yaml-file-inside-another
class Loader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(Loader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, 'r') as f:
            y = yaml.load(f)
            # set filepath key to the path of the file being loaded
            # we need this to be able to edit the config
            y['filepath'] = filename
            org_containing_dir = pathlib.Path(filename).parent.stem
            y['name'] = org_containing_dir + '-' + y['name']
            return y

Loader.add_constructor('!include', Loader.include)

class Config:
    """
    Configuration parsed directly from a YAML file
    """
    def __init__(self):
        self.config = None

    def git_last_commit(self, directory):
        '''
        get the time of the last commit
        '''
        old = os.getcwd()
        os.chdir(directory)
        cmd = "git log -1 --format=%ct"
        last_commit = subprocess.check_output(shlex.split(cmd)).decode('utf-8').strip()
        os.chdir(old)
        return last_commit

    def git_describe(self, directory):
        '''
        get the git version of the repo
        '''
        old = os.getcwd()
        os.chdir(directory)
        cmd = "git describe --tags --always --dirty"
        version = subprocess.check_output(shlex.split(cmd)).decode('utf-8').strip()

        # style fix: remove possible leading v from version
        if version[0] == 'v':
            version = version[1:]
        os.chdir(old)
        return version

    def load(self, config_file: str):
        with open(config_file, 'r') as stream:
            ok, errs = validate.validate_yaml('config.yaml.schema', config_file)
            if ok:
                print(config_file, "validated")
            else:
                print(config_file, "validation failed")
                print(errs)

            self.config = yaml.load(stream, Loader)

        if 'canonical_prog_dir' not in self.config:
            return

        self.config['nfweb_version'] = self.git_describe('.')
        print("nfweb version: ", self.config['nfweb_version'])

        for nextflow in self.get('nextflows'):
            old = os.getcwd()

            # construct the path to the git repo (presumably) containing the nextflow file
            #
            new = str(pathlib.Path(self.config['canonical_prog_dir']) / nextflow['prog_dir'])

            nextflow['last_commit'] = self.git_last_commit(new)
            nextflow['git_version'] = self.git_describe(new)
            last_commit_pretty = datetime.datetime.fromtimestamp(int(nextflow['last_commit'])).strftime("%F %T")
            nextflow['version'] = "Version: {1} Last commit: {0}".format(last_commit_pretty, nextflow['git_version'])

            print("{0} {1}".format(new, nextflow['version']))

            # for params with switch type, scan the globs array,
            # glob the directories and add them to the options
            for p in nextflow['param']['description']:
                if 'type' in p and p['type'] == 'switch':
                    if 'globs' in p:
                        for fglob in p['globs']:
                            files = glob.glob(fglob)
                            #files = pathlib.Path(glob).glob('*')
                            for f in files:
                                sf = f
                                if 'options' not in p:
                                    p['options'] = { sf: sf }
                                else:
                                    p['options'][sf] = sf
                    if 'options' not in p:
                        print(f"error: no options for switch {p['name']}")

    def load_str(self, config_str: str):
        self.config = yaml.load(config_str)

    def get(self, field: str):
        return self.config[field]
