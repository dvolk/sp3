import json
import logging
import pathlib
import threading
import time
import uuid

import treeproviders.iqtree
import treequeue


def add(my_tree_name, run_ids_sample_names, provider, user, org):
    tree_id = str(uuid.uuid4())
    treequeue.add(tree_id, my_tree_name, provider, run_ids_sample_names, user, org)
    return tree_id


def get_trees():
    return treequeue.get_all()


def get_tree(guid):
    return treequeue.get(guid)


def get_trees_containing_sample(run_uuid, sample_name):
    return treequeue.get_trees_containing_sample(run_uuid, sample_name)


iqtree = treeproviders.iqtree.IqtreeProvider()


def make_tree(provider_name, fasta_filepaths):
    if provider_name == "iqtree1":
        return iqtree.make_tree(fasta_filepaths)


fasta_files = dict()
logging.warning("building dict for fasta files")
for fasta_file in pathlib.Path("/work/persistence-catwalk/fasta").glob("**/*.fasta"):
    fasta_files[fasta_file.stem] = fasta_file
logging.warning("finished building dict")


def get_fasta_files(run_ids_sample_names):
    return [fasta_files[x] for x in json.loads(run_ids_sample_names)]


def iqtree_thread():
    while True:
        e, run_ids_sample_names = treequeue.pop("iqtree1")
        logging.warning(e)
        logging.warning(run_ids_sample_names)
        guid = e[0]
        fasta_filepaths = get_fasta_files(run_ids_sample_names)
        logging.warning(str(fasta_filepaths))
        r = make_tree("iqtree1", fasta_filepaths)
        logging.warning(str(r))
        treequeue.finish(guid, r)
        time.sleep(5)


treequeue.init()

iqtree_t = threading.Thread(target=iqtree_thread)
iqtree_t.start()
