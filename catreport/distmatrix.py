import collections, pathlib, sys, json, hashlib

def parse_fasta(content):
    content = content.split('\n')
    header = content[0]
    seq = ''.join(content[1:])
    counts = collections.Counter(seq)
    return header, seq, counts

def load_fasta(filepath):
    with open(filepath) as f:
        return parse_fasta(f.read())

class Sample:
    def __init__(self, sample_name, filepath):
        self.filepath = pathlib.Path(filepath).absolute()
        self.filename = self.filepath.name
        self.sample_name = sample_name
    def load_file(self):
        self.header, self.seq, self.counts = load_fasta(self.filepath)
        self.seq_md5 = hashlib.md5(self.seq.encode()).hexdigest()
        self.size = len(self.seq)
    def dump(self):
        return { 'header': self.header,
                 'counts': self.counts,
                 'filepath': str(self.filepath),
                 'filename': self.filename,
                 'sample_name': self.sample_name,
                 'size': self.size,
                 'seq_md5': str(self.seq_md5) }

def distance(sam1, sam2):
    ret = 0
    for c1, c2 in zip(sam1.seq, sam2.seq):
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
    ret['samples'] = { s.sample_name: s.dump() for s in samples }

    for sam1 in samples:
        ret['samples'][sam1.sample_name]['neighbours'] = dict()
        for sam2 in samples:
            if not ret['samples'][sam2.sample_name].get('neighbours'):
                ret['samples'][sam2.sample_name]['neighbours'] = dict()
            if sam1.size == sam2.size:
                dist = ret['samples'][sam1.sample_name]['neighbours'].get(sam2.sample_name)
                if dist == None:
                    dist = distance(sam1, sam2)
                ret['samples'][sam1.sample_name]['neighbours'][sam2.sample_name] = dist
                ret['samples'][sam2.sample_name]['neighbours'][sam1.sample_name] = dist

    print(json.dumps(ret, indent=4))

if __name__ == "__main__":
    main()
