import argh, glob, pathlib, json

def main(dir_glob):
    sam = list()
    for filepath in glob.glob(dir_glob + "/*"):
        p = pathlib.Path(filepath) / 'minos' / 'gvcf.fasta'
        if p.exists():
            sam.append((pathlib.Path(filepath).name, str(p)))
    print(json.dumps(sam, indent=4))

if __name__ == "__main__":
    argh.dispatch_command(main)
