from flask import Flask, abort, json, request

import catree

app = Flask(__name__)


@app.route("/submit_tree", methods=["POST"])
def submit_tree():
    print(request.json)
    run_ids_sample_names = request.json.get("run_ids_sample_names")
    my_tree_name = request.json.get("my_tree_name")
    provider = request.json.get("provider", "iqtree1")
    user = request.json.get("user", "bleh user")
    org = request.json.get("org", "bleh org")

    if not run_ids_sample_names or run_ids_sample_names == "[]":
        abort(503)

    tree_id = catree.add(my_tree_name, run_ids_sample_names, provider, user, org)
    return tree_id


@app.route("/list_trees")
def list_trees():
    run_uuid = request.args.get("pipeline_run_uuid")
    sample_name = request.args.get("sample_name")

    if run_uuid and sample_name:
        return json.dumps(catree.get_trees_containing_sample(run_uuid, sample_name))
    else:
        return json.dumps(catree.get_trees())


@app.route("/get_tree/<guid>")
def get_tree(guid):
    return json.dumps(catree.get_tree(guid))


app.run(port=7654)
