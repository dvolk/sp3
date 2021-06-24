import json
import pathlib

import waitress
import yaml
from flask import Flask, request

app = Flask(__name__)

config = yaml.load(open("config.yaml"))
output_path_prefix = pathlib.Path(config.get("output_path_prefix"))
output_url_prefix = config.get("output_url_prefix")


def make_api_response(status, details=None, data=None):
    return json.dumps({"status": status, "details": details, "data": data})


@app.route("/auth")
def auth():
    if not "X-Original-URI" in request.headers:
        abort(403)

    uri = request.headers.get("X-Original-URI")

    path = uri.split("/")

    if path[1] != "files":
        abort(403)

    print(request.authorization)

    print(uri)

    return ""


def params_to_path(dl_type, run_uuid, dl_file):
    if dl_type == "output":
        p1 = pathlib.Path(run_uuid) / dl_file
        p = output_path_prefix_p / p1
        if not p.exists():
            return None
        return output_url_prefix_p + str(p1)
    return None


@app.route("/api/download/<run_uuid>/<path:dl_file>")
def download(run_uuid, dl_file):
    url_path = params_to_path("output", run_uuid, dl_file)

    if url_path:
        return make_api_response("success", data=str(url_path))
    else:
        return make_api_response("failure")


if __name__ == "__main__":
    waitress.serve(app, listen="0.0.0.0:7300")
