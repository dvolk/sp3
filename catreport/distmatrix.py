import collections
import hashlib
import json
import pathlib
import sys


def parse_fasta(content):
    blehs = content.split("\n>")
    seqs = list()
    for i, seq in enumerate(blehs):
        lines = seq.split("\n")
        if i == 0:
            header = lines[0]
        else:
            header = ">" + lines[0]
        seq = lines[1:]
        seqs.append((header, "".join(seq)))

    max_header = str()
    max_seq = str()
    headers = list()
    for header, seq in seqs:
        headers.append([header, len(seq), collections.Counter(seq)])
        if len(seq) > len(max_seq):
            max_seq = seq
            max_header = header

    counts = collections.Counter(max_seq)
    # print(max_header, len(max_seq), counts, headers)
    return max_header, max_seq, counts, headers


def load_fasta(filepath):
    with open(filepath) as f:
        return parse_fasta(f.read())


class Sample:
    def __init__(self, sample_name, filepath):
        self.filepath = pathlib.Path(filepath).absolute()
        self.filename = self.filepath.name
        self.sample_name = sample_name

    def load_file(self):
        self.header, self.seq, self.counts, self.headers = load_fasta(self.filepath)
        self.seq_md5 = hashlib.md5(self.seq.encode()).hexdigest()
        self.size = len(self.seq)

    def dump(self):
        return {
            "header": self.header,
            "headers": self.headers,
            "counts": self.counts,
            "filepath": str(self.filepath),
            "filename": self.filename,
            "sample_name": self.sample_name,
            "size": self.size,
            "seq_md5": str(self.seq_md5),
        }


def distance(seq1, seq2):
    ret = 0
    for c1, c2 in zip(seq1, seq2):
        if c1 != c2 and c1 in "ACGT" and c2 in "ACGT":
            ret += 1
    return ret


def main():
    samples = list()

    for name, path in json.loads(sys.stdin.read()):
        s = Sample(name, path)
        samples.append(s)

    for s in samples:
        s.load_file()

    ret = dict()
    ret["samples"] = {s.sample_name: s.dump() for s in samples}

    for sam1 in samples:
        ret["samples"][sam1.sample_name]["neighbours"] = dict()
        for sam2 in samples:
            if not ret["samples"][sam2.sample_name].get("neighbours"):
                ret["samples"][sam2.sample_name]["neighbours"] = dict()
            if sam1.size == sam2.size:
                dist = ret["samples"][sam1.sample_name]["neighbours"].get(
                    sam2.sample_name
                )
                if dist == None:
                    dist = distance(sam1.seq, sam2.seq)
                ret["samples"][sam1.sample_name]["neighbours"][sam2.sample_name] = dist
                ret["samples"][sam2.sample_name]["neighbours"][sam1.sample_name] = dist

    print(json.dumps(ret, indent=4))


if __name__ == "__main__":
    main()
