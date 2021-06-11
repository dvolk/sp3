import pathlib

cmds = list()

for p in pathlib.Path('/work/reports/catreport/reports').glob('*.json'):
    p1 = p.name[0:2]
    p2 = p.name[2:4]
    out_dir = f'/work/reports/catreport/reports/{p1}/{p2}'
    cmd1 = f'mkdir -p {out_dir}'
    cmd2 = f'cp {p} {out_dir}'
    cmds.append(cmd1)
    cmds.append(cmd2)

for c in cmds:
    print(c)
