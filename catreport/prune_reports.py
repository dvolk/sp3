import pathlib
import sqlite3

import argh

con1 = sqlite3.connect("/db/catreport.sqlite")
con1.row_factory = sqlite3.Row
rows1 = con1.execute("select * from q")
con2 = sqlite3.connect("/db/catweb.sqlite")
con2.row_factory = sqlite3.Row
rows2 = con2.execute("select * from nfruns")


def go():
    paths = list(pathlib.Path("/work/reports/catreport/reports").glob("*"))
    path_uuids = [x.stem for x in paths]
    print(f"found { len(path_uuids) } files")

    # path_uuids = path_uuids[0:3]

    pipeline_uuids = dict()
    rejected = list()

    for row1 in rows1:
        pipeline_uuids[row1["uuid"]] = row1["pipeline_run_uuid"]

    print(f"loaded { len(pipeline_uuids) } rows from catreport database")

    for path_uuid in path_uuids:
        if path_uuid not in pipeline_uuids:
            rejected.append(path_uuid)

    for reject in rejected:
        print(reject)


def main():
    argh.dispatch_commands([go])


if __name__ == "__main__":
    main()
