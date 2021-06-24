import json
import os
import shlex
import subprocess
import uuid
from pathlib import Path


def get_fasta_name_nocomp(fasta_path):
    return Path(fasta_path).name.replace(".fasta", "")


def make_merged_fasta_file_nocomp(fasta_paths, out_filepath):
    with open(out_filepath, "w") as out_f:
        for fasta_path in fasta_paths:
            with open(fasta_path) as fasta_f:
                name = get_fasta_name_nocomp(fasta_path)
                seq = "".join(fasta_f.read().split("\n")[1:])
                out_f.write(f">{name}\n{seq}\n")


class IqtreeProvider:
    def __init__(self):
        self.iqtree_bin_filepath = (
            "/home/ubuntu/sp3/catree/contrib/iqtree-1.6.5-Linux/bin/iqtree"
        )
        pass

    def run_iqtree(self, work_dir):
        cmd_line = f"{self.iqtree_bin_filepath} -nt AUTO -s {work_dir}/out.mf -st DNA -m GTR+I -blmin 0.00000001"
        print(cmd_line)
        out = subprocess.check_output(shlex.split(cmd_line), cwd=work_dir)
        return out

    def make_tree(self, fasta_paths):
        id = uuid.uuid4()
        work_dir = Path(f"/work/trees/iqtree/tmp/{uuid.uuid4()}")
        work_dir.mkdir(parents=True)
        mf_filepath = work_dir / "out.mf"
        make_merged_fasta_file_nocomp(fasta_paths, mf_filepath)
        out = self.run_iqtree(work_dir).decode()

        treefile = work_dir / "out.mf.treefile"

        result = {
            "status": "success",
            "data": {
                "newick_file": str(treefile),
                "newick_content": open(treefile).read().strip(),
                "program_output": out,
                "program_filepath": self.iqtree_bin_filepath,
                "program_name": "iqtree",
                "program_version": "1.6.5",
                "time_taken": None,
            },
        }

        return result


if __name__ == "__main__":
    test_files = [
        "/home/ubuntu/sp3/catree/test/CA-0001_CO-0564.fasta",
        "/home/ubuntu/sp3/catree/test/CA-0002_CO-04808-18.fasta",
        "/home/ubuntu/sp3/catree/test/CA-0003_CO-04847-18.fasta",
    ]

    print(json.dumps(IqtreeProvider().make_tree(test_files), indent=4))
