import sys, csv, collections, pathlib

def main():
    run_dir = sys.argv[1]
    find_process = sys.argv[2]

    process_table = collections.defaultdict(list)

    trace_file = pathlib.Path('/work/runs/') / run_dir / 'trace.txt'

    with open(trace_file) as f:
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            task, tag = row['name'].split()
            tag = tag[1:-1] # remove parenthesis

            process_table[tag].append('asdf')

            if row['status'] == 'COMPLETED':
                process_table[tag].append(task)

    for task, processes in process_table.items():
        if find_process not in processes:
            print(task)

if __name__ == "__main__":
    main()
