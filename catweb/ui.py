import ast
import base64
import collections
import copy
import csv
import datetime
import glob
import hashlib
import html
import io
import json
import logging
import os
import pathlib
import re
import shlex
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from io import StringIO

import argh
import flask_login
import markdown2
import pandas
import requests
import sentry_sdk
import waitress
from flask import (
    Flask,
    abort,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user
from passlib.hash import bcrypt
from sentry_sdk.integrations.flask import FlaskIntegration
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename

import config
import db
import in_fileformat_helper
import nflib
import service_check
import utils

app = Flask(__name__)

with open(".catweb-secret-key") as f:
    app.secret_key = f.read()

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "/login"
login_manager.session_protection = "strong"

import catforum


@app.errorhandler(404)
def page500(error):
    return render_template("500.template", error=error), 404


@app.errorhandler(403)
def page500(error):
    return render_template("500.template", error=error), 403


@app.errorhandler(500)
def page500(error):
    return render_template("500.template", error=error), 500


def reload_cfg():
    global configFile
    configFile = pathlib.Path("config.yaml")
    global cfg
    cfg = config.Config()
    cfg.load(str(configFile))
    global contexts
    contexts = dict()
    for c in cfg.get("contexts"):
        contexts[c["name"]] = c
    global flows
    flows = dict()
    for f in cfg.get("nextflows"):
        flows[f["name"]] = f
    global auth_builtin
    auth_builtin = dict()
    try:
        auth_builtin = cfg.get("auth_builtin")
    except KeyError:
        pass


template_nav_links = [
    ["Dashboard", "fa fa-users fa-fw", "/"],
    ["Datasets", "fa fa-eye fa-fw", "/fetch"],
    ["Search", "fa fa-search fa-fw", "/search"],
    ["Runs/Outputs", "fa fa-file fa-fw", "/flows"],
    ["Trees", "fa fa-bullseye fa-fw", "/list_trees"],
    ["Compute", "fa fa-server fa-fw", "/cluster"],
    ["Documentation", "fa fa-bell fa-fw", "https://sp3docs.mmmoxford.uk/"],
    ["Forum", "fa fa-bank fa-fw", "/forum"],
    [
        "Report Issue",
        "fa fa-history fa-fw",
        "/forum/post/new?post_template=issue",
    ],
    ["About", "fa fa-hospital-o fa-fw", "/about"],
    ["Admin", "fa fa-cog fa-fw", "/admin"],
]


@app.route("/about")
@flask_login.login_required
def about():
    return render_template("about.template", sel="About")


# really could just be one function
def api_get_request(api, api_request):
    if not cfg.get(api):
        logging.error("api call for {api} is not in the configuration")

    host, port = cfg.get(api)["host"], cfg.get(api)["port"]
    url = f"http://{host}:{port}{api_request}"
    logging.debug(f"api_get_request() => {url}")

    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        logging.error("Failed to contact API. Is it running?")
        logging.error(e)
        abort(500, description=f"Failed to contact API: {e}")

    logging.debug(f"api_get_request() <= {r.text[:80]}")
    try:
        resp = r.json()
    except json.decoder.JSONDecodeError as e:
        logging.error("API returned data that could not be parsed as JSON")
        logging.error(e)
        abort(500, description="Could not parse API response as JSON")
    return resp.get("data")


def api_post_request(api, api_request, data_json):
    if not cfg.get(api):
        logging.error("api call for {api} not in configuration")
    host, port = cfg.get(api)["host"], cfg.get(api)["port"]
    url = f"http://{host}:{port}{api_request}"

    logging.debug(f"api_post_request() => {url}")
    try:
        r = requests.post(url, json=data_json)
    except requests.exceptions.ConnectionError as e:
        logging.error("Failed to contact API. Is it running?")
        logging.error(e)
        abort(500, description=f"Failed to contact API: {e}")

    logging.debug(f"api_post_request() <= {r.text[:80]}")
    try:
        resp = r.json()
    except json.decoder.JSONDecodeError as e:
        logging.error("API returned data that could not be parsed as JSON")
        logging.error(e)
        abort(500, description="Could not parse API response as JSON")
    return resp["data"]


class User(flask_login.UserMixin):
    def __init__(self, username):
        self.id = username
        self.u = None
        self.g = None
        self.fetch_user_data()
        self.u["token"] = session.get("token")
        logging.warning(self.u["token"])

    def fetch_user_data(self):
        if not self.u or not self.g:
            r = requests.get(
                "http://localhost:13666/get_user", params={"username": self.id}
            ).text
            logging.warning(r)
            self.u = json.loads(r)["attributes"]
            r = requests.get(
                "http://localhost:13666/get_organisation",
                params={"organisation": self.u["catweb_organisation"], "group": ""},
            ).text
            logging.warning(r)
            self.g = json.loads(r)
            if not self.g:
                return self.u, dict()
            name = self.g["name"]
            self.g = self.g["attributes"]
            self.g["name"] = name
        return self.u, self.g

    def user_data(self):
        u, _ = self.fetch_user_data()
        return u

    def org_data(self):
        _, g = self.fetch_user_data()
        return g

    def is_admin(self):
        return self.user_data().get("catweb_admin")

    def is_readonly_user(self):
        return self.user_data().get("catweb_readonly_user")

    def requires_review(self):
        return "requires_review" in self.user_data()

    def get_org_name(self):
        return self.org_data().get("name")

    #    def get_pipelines(self):
    #        return self.org_data.get("pipelines")
    def can_see_upload_dir(self, p2):
        def path_begins_with(p1, p2):
            if str(p1) >= str(p2):
                if p1[0 : len(str(p2))] == p2:
                    return True
            return False

        if path_begins_with(p2, f"/data/inputs/users/{self.id}"):
            return True
        if self.is_admin():
            return True
        for p1 in self.g.get("upload_dirs", list()):
            if path_begins_with(p2, p1):
                return True
        return False

    def email_hash(self):
        return hashlib.md5(self.user_data().get("email").encode()).hexdigest()


@login_manager.user_loader
def user_loader(username):
    return User(username)


def or_404(arg):
    if not arg:
        return abort(404)
    return arg


def icon(name):
    return f'<i class="fa fa-{name} fa-fw"></i>'


def timefmt(epochtime):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(epochtime))


def datefmt(epochtime):
    return time.strftime("%Y-%m-%d", time.localtime(epochtime))


@app.context_processor
def inject_globals():
    return {
        "catweb_version": cfg.get("catweb_version"),
        "port": port,
        "nav_links": template_nav_links,
        "icon": icon,
        "timefmt": timefmt,
        "datefmt": datefmt,
    }


@app.route("/register_sp3_user", methods=["GET", "POST"])
def register_sp3_user():
    if not cfg.get("allow_registration"):
        abort(404)
    if request.method == "GET":
        return render_template("register.template")
    if request.method == "POST":
        try:
            r = requests.get(
                "http://localhost:13666/add_user", params=request.form
            ).text
        except:
            return render_template("register.template", error="internal-error")
        if r == "OK":
            return redirect("/login?m=thanks")
        else:
            return render_template("register.template", error=r)


def is_public_fetch_source(kind):
    public_fetch_sources = ["ena1", "ena2"]

    return kind in public_fetch_sources


def check_authentication(form_username, form_password):
    r = requests.get(
        f"http://127.0.0.1:13666/check_user",
        params={"username": form_username, "password": form_password},
    )

    try:
        token = str(uuid.UUID(r.text))
        return token
    except:
        return None


@app.route("/login", methods=["GET", "POST"])
def login():
    allow_registration = cfg.get("allow_registration")

    if request.method == "GET":
        msg = request.args.get("m")

        msgs = {
            "wrong_login": "Supplied login credentials are incorrect.",
            "not_active": "User account has not been activated. Please contact the administrators after 1 day.",
            "no_org": "User is not in any organisation. Please contact the administrators.",
            "wrong_org": "User belongs to organisation with invalid configuration. Please contact the administrators.",
            "thanks": "Thank you for registering on this SP3 instance. You will be emailed when your account is activated.",
        }

        return render_template(
            "login.template",
            next=request.args.get("next"),
            msgs=msgs,
            msg=msg,
            allow_registration=allow_registration,
        )
    if request.method == "POST":
        form_username = request.form.get("username")
        form_password = request.form.get("password")

        if not (form_username and form_password):
            logging.warning(f"form submitted without username or password")
            return redirect("/")

        token = check_authentication(form_username, form_password)

        if token:
            logging.warning(f"user {form_username} verified")
        else:
            logging.warning(f"invalid credentials for user {form_username}")
            return redirect(url_for("login", m="wrong_login"))

        # --- credentials OK ---

        session.permanent = True
        session["token"] = token

        user = User(form_username)

        if user.requires_review():
            return redirect(url_for("login", m="not_active"))

        if not user.org_data():
            return redirect(url_for("login", m="no_org"))
        if not "upload_dirs" in user.org_data():
            return redirect(url_for("login", m="wrong_org"))
        if not "pipelines" in user.org_data():
            return redirect(url_for("login", m="wrong_org"))

        """
        User is authorized
        """
        flask_login.login_user(user)

        user_upload_dir = pathlib.Path(f"/data/inputs/users/{ form_username }")
        if not user_upload_dir.exists():
            user_upload_dir.mkdir()

        if request.args.get("api"):
            return "OK"

        next = request.form.get("next")
        logging.warning(f"next url: {next}")

        if (
            not next
            or next == "/None"
            or next == "None"
            or url_parse(next).netloc != ""
        ):
            next = "/"

        return redirect(next)

    assert False, "unreachable"


@app.route("/password", methods=["GET", "POST"])
@flask_login.fresh_login_required
def change_pw():
    username = current_user.id
    logging.debug(f"username: {username}")

    if request.method == "GET":
        logging.debug(f"username: {username}")
        return render_template("password.template", username=username)
    else:
        form_password1 = request.form["password1"]
        form_password2 = request.form["password2"]

        if form_password1 == form_password2:
            token = session.get("token")
            res = requests.get(
                f"http://localhost:13666/change_password/{token}",
                params={"token": token, "new_password": form_password1},
            )
            logging.debug(f"Call catdap changing password for {username}: {res}")
            if res.text == "OK":
                return redirect("/")
            else:
                return redirect("/password")
        else:

            return redirect("/")


@app.route("/logout")
def logout():
    flask_login.logout_user()
    return redirect("/")


@app.route("/am_i_logged_in")
@flask_login.login_required
def am_i_logged_in():
    return "yes"


def get_user_pipelines(username):
    ret = list()
    if current_user.is_admin():
        return flows.keys()
    else:
        return current_user.org_data().get("pipelines")


@app.route("/")
@flask_login.login_required
def status():
    org = current_user.get_org_name()
    running, recent, failed = db.get_status(org, current_user.is_admin())

    if request.args.get("api"):
        return json.dumps([running, recent, failed])

    tbl_df = run_df()
    return render_template(
        "status.template",
        sel="Dashboard",
        running=running,
        recent=recent,
        failed=failed,
        user_pipeline_list=get_user_pipelines(current_user.id),
        tbl_df=tbl_df,
    )


@app.route("/userinfo/<username>", methods=["GET", "POST"])
@flask_login.login_required
def userinfo(username: str):
    is_same = username == current_user.id

    if not is_same and not current_user.is_admin():
        return redirect("/")

    return render_template("userinfo.template")


@app.route("/flow/<flow_name>/nf_script")
@flask_login.login_required
def view_nf_script(flow_name):
    nf_script_filename = (
        pathlib.Path("/data/pipelines")
        / flows[flow_name]["prog_dir"]
        / flows[flow_name]["script"]
    )
    with open(str(nf_script_filename)) as f:
        nf_script_txt = f.read()

    return render_template(
        "view_nf_script.template", sel="Runs/Outputs", config_yaml=nf_script_txt
    )


def get_flow_config_string(flow_name):
    if not flow_name in flows:
        return make_api_response("failure", details={"missing_flow": flow_name})

    if not "filepath" in flows[flow_name]:
        return make_api_response(
            "failure", details={"missing_flow_filepath": flow_name}
        )

    with open(flows[flow_name]["filepath"], "r") as f:
        content = f.read()
    return content


@app.route("/edit_flow_config/<flow_name>")
@flask_login.login_required
def edit_flow_config(flow_name):
    config_content = get_flow_config_string(flow_name)
    return render_template(
        "view_flow_config.template", sel="Runs/Outputs", config_yaml=config_content
    )


@app.route("/admin_edit_user", methods=["GET", "POST"])
@flask_login.fresh_login_required
def admin_edit_user():
    if not current_user.is_admin():
        return redirect("/")

    username = request.args["username"]

    if request.method == "GET":
        user_data = json.dumps(
            requests.get(
                "http://localhost:13666/get_user", params={"username": username}
            ).json(),
            indent=4,
        )
        return render_template(
            "admin_edit_user.template",
            sel="Admin",
            username=username,
            user_data=user_data,
        )

    if request.method == "POST":
        requests.get(
            "http://localhost:13666/edit_user",
            params={"username": username, "user_data": request.form["user_data"]},
        )

        return redirect(f"/admin_edit_user?username={username}")


@app.route("/admin_edit_org", methods=["GET", "POST"])
@flask_login.fresh_login_required
def admin_edit_org():
    if not current_user.is_admin():
        return redirect("/")

    org_name = request.args["org_name"]

    if request.method == "GET":
        org_data = json.dumps(
            requests.get(
                "http://localhost:13666/get_organisation",
                params={"organisation": org_name},
            ).json(),
            indent=4,
        )
        return render_template(
            "admin_edit_org.template", sel="Admin", org_name=org_name, org_data=org_data
        )

    if request.method == "POST":
        requests.get(
            "http://localhost:13666/edit_organisation",
            params={"organisation": org_name, "org_data": request.form["org_data"]},
        )

        return redirect(f"/admin_edit_org?org_name={org_name}")


@app.template_filter("epochtodate")
def epochtodate(value):
    t = time.localtime(int(value))
    return f"{t.tm_year}-{t.tm_mon}-{t.tm_mday}"


@app.route("/admin")
@flask_login.fresh_login_required
def admin():
    if not current_user.is_admin():
        return redirect("/")
    services = service_check.go()
    user_d = requests.get("http://localhost:13666/get_users").json()
    organisation_d = requests.get("http://localhost:13666/get_organisations").json()
    all_org_names = [org.get("name") for org in organisation_d]

    org_to_user = collections.defaultdict(list)
    for username, u in user_d.items():
        org_to_user[u.get("attributes", dict()).get("catweb_organisation", "")].append(
            username
        )
    logging.warning(org_to_user)

    return render_template(
        "admin.template",
        sel="Admin",
        user_d=user_d,
        organisation_d=organisation_d,
        all_org_names=all_org_names,
        org_to_user=org_to_user,
        services=services,
    )


@app.route("/flows")
@flask_login.login_required
def list_flows():
    flows = list()
    for flow in cfg.get("nextflows"):
        flows.append(flow)
    if request.args.get("api"):
        return json.dumps(flows)
    return render_template(
        "list_flows.template",
        flows=flows,
        sel="Runs/Outputs",
        user_pipeline_list=get_user_pipelines(current_user.id),
    )


def get_user_params_dict(flow_name, run_uuid):
    run = db.get_pipeline_run(run_uuid)
    if not run:
        return None
    data = json.loads(run.get("data_json", "{}"))
    return data.get("user_param_dict")


def start_run(data):
    db.insert_dummy_run(data)
    cmd = f"systemd-run -p WorkingDirectory=/home/ubuntu/sp3/catweb --user /home/ubuntu/env/bin/python /home/ubuntu/sp3/catweb/go.py {shlex.quote(json.dumps(data))}"
    logging.debug(cmd)
    os.system(cmd)


def new_run1(flow_name, flow_cfg, form):
    logging.debug(f"flow_cfg: {flow_cfg}")

    run_uuid = str(uuid.uuid4())

    run_name = form["run_name"]
    context = form["context"]
    fetch_uuid = form["fetch_uuid"]

    try:
        api_post_request(
            "catpile_api",
            "/fetch_to_run",
            json.dumps({"fetch_uuid": fetch_uuid, "pipeline_run_uuid": run_uuid}),
        )
    except Exception as e:
        logging.error(f"catpile failed linking fetch and run: {str(e)}")

    reference_map = "{}"
    if "ref_uuid" in form and form["ref_uuid"] and "refmap" in flow_cfg:
        logging.debug(f'ref_uuid: \'{form["ref_uuid"]}\'')
        r = db.get_reference_cache(ref_uuid)
        reference_map = r.get("reference_json")
        logging.debug(f"reference_map: {reference_map}")

    # user parameters, grabbed from run from
    user_param_dict = dict()

    indir = ""
    readpat = ""

    for form_key, form_value in form.items():
        if "-and-" in form_key:
            name, arg = form_key.split("-and-")

            if form_value != "":
                user_param_dict[arg] = form_value

            if name == "indir":
                indir = form_value
            elif name == "readpat":
                readpat = form_value

    data = {
        # catweb run uuid (not to be confused with the uuid generated by nextflow)
        "run_uuid": run_uuid,
        # run name / project name
        "run_name": run_name,
        # execution context (i.e. local or slurm or whatever)
        "context": context,
        # flow config
        "flow_cfg": flow_cfg,
        # individual sample reference map
        "reference_map": reference_map,
        # contexts
        "contexts": contexts,
        # user arguments to nextflow
        "user_param_dict": user_param_dict,
        # web user id that started the run
        "user_name": current_user.id,
        # input directory (if it exists or "" otherwise)
        "indir": indir,
        # filtering regular expression (if it exists or "" otherwise)
        "readpat": readpat,
    }

    start_run(data)
    return run_uuid


@app.route("/flow/<flow_name>/new", methods=["GET", "POST"])
@flask_login.login_required
def begin_run(flow_name: str):
    if flow_name not in flows:
        abort(404, description="Flow not found")

    # we copy here because we are adding dynamic globs below
    # which are added every time the form is loaded
    flow_cfg = copy.deepcopy(flows[flow_name])

    """
    GET
    """
    if request.method == "GET":
        # input directory, grabbed from query string
        fetch_given_input = ""
        # user parameters, grabbed from run from
        user_param_dict = dict()

        fetch_given_input_b = ""
        fetch_uuid = ""

        sample_names = list()
        references = list()
        sample_names_references = list()

        # rebuild dynamic globs
        for p in flow_cfg["param"]["description"]:
            if "type" in p and p["type"] == "switch":
                for fglob in p.get("dynamic-globs", list()):
                    files = glob.glob(fglob)
                    logging.warning("adding {files}")
                    for f in files:
                        p["options"][f] = f

        guessed_filename_format = ""
        # allow prefilling of the form from the fetch page
        if request.args.get("given_input"):
            fetch_given_input_b = request.args.get("given_input")
            fetch_given_input = base64.b16decode(fetch_given_input_b).decode("utf-8")
            # try to get the sample names and reference
            guessed_filename_format, sample_names = in_fileformat_helper.guess_from_dir(
                fetch_given_input
            )
            if sample_names:
                for p in flow_cfg["param"]["description"]:
                    if p["name"] == "ref":
                        for k, v in p["options"].items():
                            references.append(v)
        # allow prefilling of the form from other runs
        elif request.args.get("replay"):
            replay_uuid = request.args.get("replay")
            user_param_dict = get_user_params_dict(flow_name, replay_uuid)

        if request.args.get("fetch_uuid"):
            fetch_uuid = request.args.get("fetch_uuid")

        ref_uuid = str()
        if request.args.get("ref_uuid"):
            ref_uuid = request.args.get("ref_uuid")

        logging.debug(sample_names)
        logging.debug(references)
        return render_template(
            "start_run.template",
            sel="Runs/Outputs",
            ref_uuid=ref_uuid,
            flow_cfg=flow_cfg,
            sample_names=sample_names,
            references=references,
            given_input=fetch_given_input,
            fetch_given_input_b=fetch_given_input_b,
            now=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            user_param_dict=user_param_dict,
            guessed_filename_format=guessed_filename_format,
            fetch_uuid=fetch_uuid,
        )

    elif request.method == "POST":
        logging.debug(f"form: {request.form}")
        run_uuid = new_run1(flow_name, flow_cfg, request.form)
        if request.form.get("api"):
            return json.dumps({"run_uuid": run_uuid})
        else:
            return redirect(f"/flow/{flow_name}")


@app.route("/map_samples", methods=["POST"])
@flask_login.login_required
def map_samples():
    if "sample_names" in request.form:
        # display table
        if "fetch_uuid" in request.form:
            fetch_uuid = request.form["fetch_uuid"]
        else:
            fetch_uuid = ""
        return render_template(
            "refmap.template",
            sel="Runs/Outputs",
            sample_names=ast.literal_eval(request.form["sample_names"]),
            references=ast.literal_eval(request.form["references"]),
            flow_name=request.form["flow_name"],
            fetch_given_input_b=request.form["fetch_given_input_b"],
            fetch_uuid=fetch_uuid,
        )
    else:
        # save results in database and redirect to new run
        reference_map = dict()
        logging.warning(str(request.form))
        for k, v in request.form.items():
            if k[0:5] == "_ref_":
                logging.debug(f"{k}={v}")
                sample_name = k[5:]
                reference = v
                reference_map[sample_name] = reference
        ref_uuid = str(uuid.uuid4())
        data = {"ref_uuid": ref_uuid, "reference_json": reference_map}
        if "fetch_uuid" in request.form:
            fetch_uuid = request.form["fetch_uuid"]
        else:
            fetch_uuid = ""

        logging.debug(f"form data: {data}")
        if "cancel" in request.form:
            return redirect(
                f'/flow/{ request.form["flow_name"] }/new?given_input={ request.form["fetch_given_input_b"] }&fetch_uuid={ fetch_uuid }'
            )
        else:
            db.add_to_reference_cache(data["ref_uuid"], data["reference_json"])
            return redirect(
                f'/flow/{ request.form["flow_name"] }/new?given_input={ request.form["fetch_given_input_b"] }&ref_uuid={ ref_uuid }&fetch_uuid={ fetch_uuid }'
            )


@app.route("/api/flow/run_and_status/<pipeline_name>")
@flask_login.login_required
def run_and_status(pipeline_name):
    return json.dumps(db.get_run_and_status(pipeline_name), indent=4)


@app.route("/flow/<pipeline_name>")
@flask_login.login_required
def list_runs(pipeline_name):
    flow_cfg = flows.get(pipeline_name)
    if not flow_cfg:
        abort(404)
    pipeline_runs = db.get_pipeline_runs(pipeline_name)

    has_dagpng = False
    if pathlib.Path(f"/data/pipelines/dags/{pipeline_name}.png").is_file():
        has_dagpng = True

    if request.args.get("api"):
        if request.args.get("api") == "v1":
            return json.dumps(pipeline_runs)
        if request.args.get("api") == "v2":
            return json.dumps([run["run_uuid"] for run in pipeline_runs])
        if request.args.get("api") == "v3":
            return json.dumps(db.get_run_and_status(pipeline_name))

    if "no_sample_count" in flow_cfg.keys():
        pipeline_cfg = {
            "display_name": flow_cfg.get("display_name"),
            "flow_name": flow_cfg.get("name"),
            "no_sample_count": flow_cfg.get("no_sample_count"),
        }
    else:
        pipeline_cfg = {
            "display_name": flow_cfg.get("display_name"),
            "flow_name": flow_cfg.get("name"),
        }

    return render_template(
        "list_runs.template",
        sel="Runs/Outputs",
        pipeline_runs=pipeline_runs,
        pipeline_cfg=pipeline_cfg,
        has_dagpng=has_dagpng,
    )


@app.route("/flow/<flow_name>/dagpng")
@flask_login.login_required
def show_dagpng(flow_name):
    if not flow_name in flows:
        abort(404, description="Flow not found")

    dagpng_path = f"/data/pipelines/dags/{flow_name}.png"

    if not pathlib.Path(dagpng_path).is_file():
        abort(404, description="DAG png file not found")

    with open(dagpng_path, "rb") as f:
        dagpng_b64 = base64.b64encode(f.read()).decode()

    return render_template(
        "show_dagpng.template",
        sel="Runs/Outputs",
        flow_name=flow_name,
        dagpng_b64=dagpng_b64,
    )


@app.route("/flow/<flow_name>/go_details/<run_uuid>")
@flask_login.login_required
def go_details(flow_name, run_uuid):
    # remove flow_name
    log_dir = cfg.get("log_dir")
    log_filename = pathlib.Path(log_dir) / "{run_uuid}.log"

    with open(str(log_filename)) as lf:
        content = lf.read()

    return render_template(
        "show_log.template", content=content, uuid=uuid, sel="Runs/Outputs"
    )


def task_details(run_uuid, task_id):
    """
    return the .command.* files in the nextflow task directory
    """

    data = db.get_run(run_uuid)
    nf_directory = pathlib.Path(data[0][11])

    work_dir = nf_directory / "runs" / run_uuid / "work"
    if not work_dir.is_dir():
        return None

    logging.debug(work_dir)

    truncated_task_subdir = task_id.replace("-", "/")
    full_task_subdir = list(work_dir.glob(truncated_task_subdir + "*"))
    if not full_task_subdir:
        return None

    full_task_subdir = full_task_subdir[0]

    if not full_task_subdir.is_dir():
        return None

    """
    dictionary of { filename: file contents }
    """
    file_contents = {}
    for filename in full_task_subdir.glob("*"):
        if filename.is_file() and ".command." in str(filename):
            with open(str(filename), "r") as f:
                file_contents[str(filename.name)] = f.read()

    return file_contents


@app.route("/flow/<flow_name>/details/<run_uuid>/task/<sample_name>/<task_name>")
@flask_login.login_required
def run_details_task_nice(flow_name, run_uuid, sample_name, task_name):
    """
    Get and load the json string containing the ordered trace dict
    """
    trace_nice = make_nice_trace(run_uuid)

    task_id_encoded = None
    if sample_name in trace_nice:
        for task in trace_nice[sample_name]:
            if task["nice_name"] == task_name:
                task_id = task["hash"]
        task_id_encoded = task_id.replace("/", "-")

    data = db.get_run(run_uuid)
    run_name = data[0][19]
    files = task_details(run_uuid, task_id_encoded)

    return render_template(
        "show_task.template",
        sel="Runs/Outputs",
        flow_name=flow_name,
        run_uuid=run_uuid,
        task_id=task_id,
        sample_name=sample_name,
        task_name=task_name,
        files=files,
        run_name=run_name,
        flow_display_name=flows[flow_name]["display_name"],
    )

    return run_details_task(flow_name, run_uuid, task_id_encoded)


@app.route("/flow/<flow_name>/details/<run_uuid>/task/<task_id>")
@flask_login.login_required
def run_details_task(flow_name, run_uuid, task_id):
    if len(task_id) != 9:
        abort(404, description="Task not found")

    files = task_details(run_uuid, task_id)

    data = db.get_run(run_uuid)
    run_name = data[0][19]

    return render_template(
        "show_task.template",
        sel="Runs/Outputs",
        flow_name=flow_name,
        run_uuid=run_uuid,
        task_id=task_id,
        sample_name="",
        task_name="",
        files=files,
        run_name=run_name,
        flow_display_name=flows[flow_name]["display_name"],
    )


def get_sample_tags_for_run(run_uuid):
    rows = api_get_request("cattag_api", f"/get_sample_tags_for_run/{run_uuid}")
    ret = collections.defaultdict(list)
    for row in rows:
        ret[row[0]].append([row[1], row[2]])
    print(ret)
    return ret


def make_nice_trace(run_uuid):
    data = db.get_run(run_uuid)
    trace = nflib.parse_nextflow_trace(db.load_nextflow_trace(run_uuid))

    """
    dict from sample/nextflow tag to list of trace entries with that sample

    trace entries that couldn't be parsed go into the "unknown" key
    """
    trace_nice = collections.OrderedDict()
    trace_nice["unknown"] = []

    """
    Construct trace_nice
    """
    for entry in trace:
        m = re.search("(.*) \((.*)\)", entry["name"])
        if not m:
            trace_nice["unknown"].append(entry)
            continue
        task_name = m.group(1)
        dataset_id = m.group(2)
        entry["nice_name"] = task_name
        entry["dataset_id"] = dataset_id
        if dataset_id in trace_nice:
            trace_nice[dataset_id].append(entry)
        else:
            trace_nice[dataset_id] = [entry]

    return trace_nice


def get_details(flow_name, run_uuid):
    data = db.get_run(run_uuid)

    # root_dir is entry 11
    nf_directory = pathlib.Path(data[0][11])
    output_dir = pathlib.Path(data[0][13])
    input_dir = pathlib.Path(json.loads(data[0][20])["indir"])
    run_name = data[0][19]

    buttons = {}

    if output_dir.is_dir():
        buttons["output_files"] = True
        buttons["fetch"] = True

    if input_dir.is_dir():
        buttons["rerun"] = True

    pid_filename = nf_directory / "runs" / run_uuid / ".run.pid"
    if pid_filename.is_file():
        buttons["stop"] = True

    log_filename = nf_directory / "runs" / run_uuid / ".nextflow.log"
    if log_filename.is_file():
        buttons["log"] = True

    if db.nextflow_file_exists(run_uuid, "report.html"):
        buttons["report"] = True

    if db.nextflow_file_exists(run_uuid, "timeline.html"):
        buttons["timeline"] = True

    trace = nflib.parse_nextflow_trace(db.load_nextflow_trace(run_uuid))
    return trace, output_dir, buttons, run_name


@app.route("/flow/<flow_name>/details/<run_uuid>")
@flask_login.login_required
def run_details(flow_name, run_uuid):
    rows = db.get_run(run_uuid)
    if not rows:
        abort(404, description="Run not found")

    # get fetch id from catpile
    r = requests.get(f"http://localhost:22000/get_fetch_for_run/{run_uuid}").json()
    if r:
        fetch_uuid = r
    else:
        fetch_uuid = None
    logging.warning(fetch_uuid)

    data = json.loads(rows[0][20])
    user_param_dict = data["user_param_dict"]

    trace, output_dir, buttons, run_name = get_details(flow_name, run_uuid)

    """
    Get and load the json string containing the ordered trace dict
    """
    sample_count = 0
    task_count = 0
    expected_tasks = 0
    trace_nice = make_nice_trace(run_uuid)

    """
    Count samples and tasks, subject to certain filters
    """
    for dataset_id, tasks in trace_nice.items():
        if dataset_id != "unknown":
            for task in tasks:
                if task["status"] == "COMPLETED":
                    if "count_tasks_ignore" in flows[flow_name]:
                        if (
                            task["nice_name"]
                            not in flows[flow_name]["count_tasks_ignore"]
                        ):
                            task_count += 1
                    else:
                        task_count += 1

    """
    Get number of input samples and calculate the number of expected tasks (samples * tasks_per_sample)
    """
    input_files_count, output_files_count = db.get_input_files_count(run_uuid)
    if input_files_count > 0:
        if "count_tasks_per_sample" in flows[flow_name]:
            expected_tasks = (
                input_files_count * flows[flow_name]["count_tasks_per_sample"]
            )
            logging.debug(f"expected tasks: {expected_tasks}")

    logging.debug(f"samples: {len(trace_nice)} task count: {task_count}")

    fetch_dir = output_dir

    fetch_id = base64.b16encode(bytes(str(fetch_dir), encoding="utf-8")).decode("utf-8")

    tags = get_sample_tags_for_run(run_uuid)

    if request.args.get("api"):
        return json.dumps(
            {"tags": tags, "trace": trace, "trace_nice": trace_nice, "data": rows}
        )

    if flow_name in flows:
        flow_cfg = flows[flow_name]
        if "no_sample_report" in flow_cfg.keys():
            pipeline_no_report = True
        else:
            pipeline_no_report = False
    else:
        abort(404, description="Flow not found")

    return render_template(
        "run_details.template",
        sel="Runs/Outputs",
        uuid=run_uuid,
        flow_name=flow_name,
        tags=tags,
        flow_display_name=flows[flow_name]["display_name"],
        entries=trace,
        output_dir=str(output_dir),
        buttons=buttons,
        fetch_id=fetch_id,
        trace_nice=trace_nice,
        run_name=run_name,
        user_param_dict=user_param_dict,
        task_count=task_count,
        expected_tasks=expected_tasks,
        pipeline_no_report=pipeline_no_report,
        fetch_uuid=fetch_uuid,
    )


def get_log(flow_name, run_uuid):
    data = db.get_run(run_uuid)

    nf_directory = pathlib.Path(data[0][11])

    # Using root_dir
    log_filename = nf_directory / "runs" / run_uuid / ".nextflow.log"
    with open(str(log_filename)) as f:
        return f.read()


@app.route("/flow/<flow_name>/log/<run_uuid>")
@flask_login.login_required
def show_log(flow_name, run_uuid):
    content = get_log(flow_name, run_uuid)
    return render_template(
        "show_log.template",
        sel="Runs/Outputs",
        content=content,
        flow_name=flow_name,
        uuid=run_uuid,
    )


def get_output_files(flow_name, run_uuid):
    data = db.get_run(run_uuid)
    # Using root_dir
    output_dir = data[0][13]

    du_cmd = ["du", "-sh", output_dir]
    tree_cmd = ["tree", output_dir]

    logging.debug(f"du command: {du_cmd}")
    try:
        du_p = subprocess.check_output(
            du_cmd, stderr=subprocess.PIPE, universal_newlines=True
        )
    except subprocess.CalledProcessError:
        return make_api_response("failure", details={"command_failed": "du"})

    logging.debug(f"tree command: {tree_cmd}")
    try:
        result = dict()

        def try_tree(result):
            result["result"] = subprocess.check_output(
                tree_cmd, stderr=subprocess.PIPE, universal_newlines=True
            )

        t = threading.Thread(target=try_tree, args=(result,))
        t.start()
        t.join(timeout=3)
        tree_p = result["result"]
    except KeyError:
        tree_p = "\n\ntree command failed with timeout\n\n"

    # Format directory on top, then total size, then the file tree
    size_str = du_p.strip()
    size_str = size_str.split("\t")
    size_str = f"Total size: {size_str[0]}"
    out_str = tree_p.strip().split("\n")
    out_str = "\n".join(
        [out_str[0].strip()] + [out_str[-1]] + [size_str] + [""] + out_str[1:-1]
    )

    return out_str


@app.route("/flow/<flow_name>/output_files/<run_uuid>")
@flask_login.login_required
def show_output_files(flow_name, run_uuid):
    content = get_output_files(flow_name, run_uuid)
    download_url = cfg.get("download_url")

    return render_template(
        "show_files.template",
        sel="Runs/Outputs",
        content=content,
        flow_name=flow_name,
        uuid=run_uuid,
        download_url=download_url,
    )


cmds = list()


def once_cmd_async(cmd):
    """
    run a system command in a thread, but only once
    """
    if cmd not in cmds:
        logging.warning(f"once_cmd_async: {cmd}")

        def f(cmd):
            os.system(cmd)

        cmds.append(cmd)
        threading.Thread(target=f, args=(cmd,)).start()

    return True


def do_delete_output_files(run_uuid):
    try:
        uuid.UUID(run_uuid)
        once_cmd_async(f"rm -rf /work/output/{run_uuid}")
    except Exception as e:
        logging.error(e)


def do_delete_run(run_uuid):
    try:
        uuid.UUID(run_uuid)
        db.delete_run(run_uuid)
        once_cmd_async(f"rm -rf /work/runs/{run_uuid}")
        once_cmd_async(f"rm -rf /work/output/{run_uuid}")
    except Exception as e:
        logging.error(e)


@app.route("/flow/<flow_name>/delete_output_files/<run_uuid>")
def delete_output_files(flow_name, run_uuid):
    do_delete_output_files(run_uuid)
    return redirect(f"/flow/{flow_name}/details/{run_uuid}")


@app.route("/flow/<flow_name>/delete_run/<run_uuid>")
def delete_run(flow_name, run_uuid):
    do_delete_run(run_uuid)
    return redirect(f"/flow/{flow_name}")


def get_report_html(flow_name, run_uuid):
    content = db.load_nextflow_file(run_uuid, "report.html")

    try:
        import process_report_html

        js = process_report_html.get_report_json(report_filename)
    except Exception as e:
        logging.error(f"process report failed: {run_uuid}: {str(e)}")
        js = ""

    return content, js


@app.route("/flow/<flow_name>/report/<run_uuid>")
@flask_login.login_required
def show_report(flow_name, run_uuid):
    content, js = get_report_html(flow_name, run_uuid)

    if request.args.get("api"):
        return js
    if request.args.get("csv"):
        trace = js["trace"]
        table = pandas.read_json(io.StringIO(trace))
        table = table.drop(["script", "env"], axis=1)
        return "<pre>" + table.sort_values("tag").to_csv(index=False)

    return content


def get_timeline(flow_name, run_uuid):
    return db.load_nextflow_file(run_uuid, "timeline.html")


@app.route("/flow/<flow_name>/timeline/<run_uuid>")
@flask_login.login_required
def show_timeline(flow_name: str, run_uuid: int):
    content = get_timeline(flow_name, run_uuid)
    return content


def get_dagdot(run_uuid):
    data = db.get_run(run_uuid)
    nf_directory = pathlib.Path(data[0][11])
    dagdot_filename = nf_directory / "runs" / runs_uuid / "dag.dot"

    with open(str(dagdot_filename)) as f:
        content = f.read()

    return content


@app.route("/flow/<flow_name>/dagdot/<run_uuid>")
@flask_login.login_required
def show_dagdot(flow_name, run_uuid):
    content = get_dagdot(run_uuid)
    return content


def stop_run(run_uuid):
    pid_filename = pathlib.Path(f"/work/runs/{run_uuid}/.run.pid")
    if pid_filename.exists():
        with open(str(pid_filename)) as f:
            pid = int(f.readline())
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            logging.error(f"stop_run(): process doesn't exist")
    else:
        logging.error(f"pid filename {pid_filename} doesnt exist")


@app.route("/flow/<flow_name>/stop/<run_uuid>")
@flask_login.login_required
def kill_nextflow(flow_name, run_uuid):
    stop_run(run_uuid)
    return redirect(f"/flow/{flow_name}")


@app.route("/terminate_job/<job_id>")
@flask_login.login_required
def terminate_job(job_id):
    if not current_user.is_admin():
        abort(403)
    requests.get(f"http://127.0.0.1:6000/terminate/{ job_id }")
    return redirect("/cluster")


def hm_timediff(epochtime_start, epochtime_end):
    t = epochtime_end - epochtime_start
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    else:
        return f"{m}m"


@app.route("/storage_analysis")
@flask_login.login_required
def storage_analysis():
    try:
        with open("/db/catspace_result.txt") as f:
            catspace_result = json.loads(f.read())
        catspace_all_sorted = sorted(
            catspace_result,
            key=lambda row: row["du_run_space"] + row["du_output_space"],
            reverse=True,
        )
    except Exception as e:
        logging.error(str(e))
        catspace_all_sorted = list()

    for row in catspace_all_sorted:
        row["total"] = row["du_run_space"] + row["du_output_space"]

    total_used_run = sum([row["du_run_space"] for row in catspace_all_sorted])
    total_used_output = sum([row["du_output_space"] for row in catspace_all_sorted])

    return render_template(
        "storage_analysis.template",
        sel="Compute",
        catspace_all_sorted=catspace_all_sorted,
        total_used_run=total_used_run,
        total_used_output=total_used_output,
    )


def run_df():
    try:
        df = subprocess.check_output(
            shlex.split("df -h"), stderr=subprocess.PIPE, universal_newlines=True
        )
    except FileNotFoundError as e:
        abort(500, description=e)
    except subprocess.CalledProcessError as e:
        abort(500, description=e)
    disk_filter = cfg.get("cluster_view")["disk_filter"]
    tbl_df = pandas.read_csv(StringIO(df), sep="\s+")
    tbl_df = tbl_df[tbl_df.Filesystem.str.contains(disk_filter)][
        ["Mounted", "Use%", "Used", "Size"]
    ]
    return tbl_df


@app.route("/cluster")
@flask_login.login_required
def cluster():
    try:
        r = requests.get("http://127.0.0.1:6000/status").json()
        cluster_info = r["nodes"]
    except Exception as e:
        abort(500, description=e)

    for node_name, node in cluster_info.items():
        for j in node["jobs"]:
            for job_id, job in j.items():
                job["duration"] = hm_timediff(job["started"], int(time.time()))

    tbl_df = run_df()

    return render_template(
        "cluster.template", sel="Compute", cluster_info=cluster_info, tbl_df=tbl_df
    )


@app.route("/drop_upload")
@flask_login.login_required
def upload_data():
    subfolder = str(uuid.uuid4())
    rootpath = pathlib.Path(f"/data/inputs/users/{ current_user.id }")
    newpath = str(rootpath / subfolder)
    newpath_encoded = base64.b16encode(bytes(newpath, encoding="utf-8")).decode("utf-8")

    return render_template(
        "upload.template",
        sel="Datasets",
        subfolder=subfolder,
        fetchpath=newpath,
        fetchpath_encoded=newpath_encoded,
    )


@app.route("/drop_upload/<subfolder>", methods=["POST"])
@flask_login.login_required
def upload_data2(subfolder):
    file = request.files["file"]
    if file.filename[-9:] == ".fastq.gz" or file.filename[-4:] == ".bam":
        rootpath = pathlib.Path(f"/data/inputs/users/{ current_user.id }")
        newpath = str(rootpath / subfolder)
        logging.warning(newpath)
        if not (os.path.isdir(newpath)):
            os.mkdir(newpath)
        save_path = os.path.join(newpath, secure_filename(file.filename))
        logging.warning(save_path)
        with open(save_path, "ab") as f:
            f.seek(int(request.form["dzchunkbyteoffset"]))
            f.write(file.stream.read())
        return make_response(("Uploaded Chunk", 200))
    else:
        return make_response(("File format not permitted", 415))


@app.route("/fetch_data")
@flask_login.login_required
def fetch_data():
    r = api_get_request("fetch_api", "/api/fetch/describe")
    sources = r["sources"]

    return render_template("new_fetch.template", sel="Datasets", sources=sources)


@app.route("/get_files", methods=["POST"])
@flask_login.login_required
def get_files():
    req = request.get_json()
    if "path" not in req:
        abort(403)
    path = req["path"]
    # return json.dumps([str(x.name) for x in pathlib.Path(path).glob('*')])
    filenames = os.listdir(path)
    dict_filenames = dict(filenames=filenames)
    return jsonify(dict_filenames)


@app.route("/fetch_data2/<fetch_kind>")
@flask_login.login_required
def fetch_data2(fetch_kind):
    r = api_get_request("fetch_api", "/api/fetch/describe")
    source = r.get("sources", dict()).get(fetch_kind)
    if not source:
        abort(404)

    # allow prefilling of the new fetch form
    in_data_kind = None
    in_data_identifier = None

    if "kind" in request.args and "id" in request.args:
        in_data_kind = request.args.get("kind")
        in_data_identifier = request.args.get("id")
        in_data_identifier = base64.b16decode(in_data_identifier).decode("utf-8")

    paths = list()
    if "local_glob_directories" in source:
        for d in source["local_glob_directories"]:
            if current_user.can_see_upload_dir(d):
                for p in glob.glob(d):
                    paths.append(p)
    paths.sort()

    if fetch_kind == "ena1":
        return render_template(
            "new_fetch2_ena1.template",
            sel="Datasets",
            source=source,
            fetch_kind=fetch_kind,
            data_kind=in_data_kind,
            data_identifier=in_data_identifier,
            paths=paths,
        )
    if fetch_kind == "ena2":
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = "ENA_" + timestamp
        return render_template(
            "new_fetch2_ena2.template",
            sel="Datasets",
            name=name,
            source=source,
            fetch_kind=fetch_kind,
            data_kind=in_data_kind,
            data_identifier=in_data_identifier,
            paths=paths,
        )

    if fetch_kind == "local1":
        return render_template(
            "new_fetch2_local1.template",
            sel="Datasets",
            source=source,
            fetch_kind=fetch_kind,
            data_kind=in_data_kind,
            data_identifier=in_data_identifier,
            paths=paths,
        )
    abort(404)


@app.route("/fetch")
@flask_login.login_required
def fetch():
    r = api_get_request("fetch_api", "/api/fetch/status")
    r2 = api_get_request("fetch_api", "/api/fetch/describe")

    sources = r2["sources"]

    # TODO error checking
    fetches = r

    # change the epoch time in a human-readable format
    # and reformat the output_dir into base 16
    for k, v in fetches.items():
        pretty_started_date = datetime.datetime.fromtimestamp(v["started"]).strftime(
            "%F %T"
        )

        output_dir = str(pathlib.Path(sources[v["kind"]]["flatten_directory"]) / k)
        output_dir_b16 = base64.b16encode(bytes(output_dir, encoding="utf-8")).decode(
            "utf-8"
        )

        v.update({"started": pretty_started_date, "output_dir": output_dir_b16})

    # filter fetches by what the user can see
    logging.warning(fetches)
    user_fetches = dict()
    for k, v in fetches.items():
        if is_public_fetch_source(v["kind"]) or current_user.can_see_upload_dir(
            v["name"]
        ):
            user_fetches[k] = v
    fetches = user_fetches
    logging.warning(fetches)

    # sort fetches by time
    fetches = dict(reversed(sorted(fetches.items(), key=lambda x: x[1]["started"])))

    return render_template(
        "fetch.template", sel="Datasets", fetches=fetches, sources=sources
    )


@app.route("/fetch_new", methods=["POST"])
@flask_login.login_required
def fetch_new():
    fetch_name = request.form.get("fetch_name")
    fetch_range = request.form.get("fetch_range")
    fetch_kind = request.form.get("fetch_kind")
    fetch_method = request.form.get("fetch_method")
    fetch_samples = request.form.get("fetch_samples")

    r = api_post_request(
        "fetch_api",
        f"/api/fetch/{fetch_kind}/new",
        {
            "fetch_name": fetch_name,
            "fetch_range": fetch_range,
            "fetch_method": fetch_method,
            "fetch_samples": fetch_samples,
        },
    )

    if request.form.get("is_api"):
        return json.dumps(r)

    return redirect("/fetch")


@app.route("/fetch_delete/<fetch_kind>/<guid>")
@flask_login.login_required
def fetch_delete(fetch_kind, guid):
    api_get_request("fetch_api", f"/api/fetch/{fetch_kind}/delete/{guid}")
    return redirect("/fetch")


@app.route("/fetch_stop/<guid>")
@flask_login.login_required
def fetch_stop(guid):
    url = api_get_request("fetch_api", f"/api/fetch/stop/{guid}")
    return redirect("/fetch")


@app.route("/select_flow/<guid>")
@flask_login.login_required
def select_flow(guid):
    ret1 = api_get_request("fetch_api", f"/api/fetch/status_sample/{guid}")

    flow_name = None
    if request.args.get("flow_name"):
        flow_name = request.args.get("flow_name")
    if guid in ret1:
        ret1 = ret1[guid]
    else:
        abort(404, description="guid not found")

    if ret1:
        print(ret1)
        accession = ret1["name"]
        logging.debug(ret1)
        fetch_range = json.loads(ret1["data"])["fetch_range"]
        status = ret1["status"]
        progress = ret1["progress"]
        total = ret1["total"]
        kind = ret1["kind"]

        r = api_get_request("fetch_api", "/api/fetch/describe")
        sources = r["sources"]

        input_dir = pathlib.Path(sources[kind]["flatten_directory"]) / guid

    r2 = api_get_request("fetch_api", "/api/fetch/describe")
    sources = r2["sources"]
    output_dir = str(pathlib.Path(sources[ret1["kind"]]["flatten_directory"]) / guid)
    output_dir_b16 = base64.b16encode(bytes(output_dir, encoding="utf-8")).decode(
        "utf-8"
    )

    # Get the first name of the nextflow and all of them,
    # to allow users to change what to run
    all_flow_names = [x["name"] for x in cfg.get("nextflows")]

    user_pipelines = get_user_pipelines(current_user.id)
    if not flow_name:
        if user_pipelines:
            flow_name = list(user_pipelines)[0]

    return render_template(
        "select_flow.template",
        sel="Datasets",
        guid=guid,
        name=accession,
        fetch_range=fetch_range,
        status=status,
        progress=progress,
        total=total,
        flow_name=flow_name,
        input_dir=input_dir,
        output_dir_b16=output_dir_b16,
        user_pipelines=user_pipelines,
    )


@app.route("/flow/<flow_name>/show_metadata/<pipeline_run_uuid>")
@flask_login.login_required
def fetch_metadata(flow_name, pipeline_run_uuid):
    sp3data = api_get_request(
        "catpile_api", f"/get_sp3_data_for_run/{pipeline_run_uuid}"
    )
    sp3data = list(enumerate(sp3data))

    return render_template(
        "show_sp3data.template",
        sel="Runs/Outputs",
        pipeline_run_uuid=pipeline_run_uuid,
        sp3data=sp3data,
    )


@app.route("/fetch_details/<guid>")
@flask_login.login_required
def fetch_details(guid):
    ret1 = api_get_request("fetch_api", f"/api/fetch/status_sample/{guid}")

    if guid in ret1:
        ret1 = ret1[guid]
    else:
        abort(404, description="guid not found")

    if request.args.get("api"):
        return json.dumps(ret1)

    ret2 = api_get_request("fetch_api", f"/api/fetch/log/{guid}")

    fetch_samples = []
    if ret1:
        accession = ret1["name"]
        logging.debug(ret1)
        fetch_range = json.loads(ret1["data"])["fetch_range"]
        fetch_sampels = []
        if "fetch_samples" in ret1["data"]:
            fetch_samples = json.loads(ret1["data"])["fetch_samples"]
        status = ret1["status"]
        progress = ret1["progress"]
        total = ret1["total"]
        kind = ret1["kind"]

        r = api_get_request("fetch_api", "/api/fetch/describe")
        sources = r["sources"]

        input_dir = pathlib.Path(sources[kind]["flatten_directory"]) / guid

    file_table = list()
    if ret1:
        if "ok_files_fastq_ftp" in ret1:
            for i, ok_file in enumerate(ret1["ok_files_fastq_ftp"]):
                file_table.append([ok_file, ret1["ok_files_fastq_md5"][i]])

    app_log = ret2["app"]

    ena_table = ""
    sp3data = None
    if "ena" in ret2 and ret2["ena"]:
        logging.debug(ret2["ena"][:80])
        pandas.set_option("display.max_colwidth", -1)
        ena_table = (
            pandas.read_json(ret2["ena"]).stack().sort_index().to_frame().to_html()
        )
    else:
        sp3data = api_get_request("catpile_api", f"/get_sp3_data_for_fetch/{guid}")
        sp3data = list(enumerate(sp3data))

    return render_template(
        "fetch_details.template",
        sel="Datasets",
        guid=guid,
        name=accession,
        fetch_range=fetch_range,
        fetch_samples=fetch_samples,
        status=status,
        progress=progress,
        total=total,
        file_table=file_table,
        log=app_log,
        input_dir=input_dir,
        ena_table=ena_table,
        sp3data=sp3data,
    )


@app.route("/flow/<run_uuid>/<dataset_id>/report_pdf")
@flask_login.login_required
def get_report_pdf(run_uuid, dataset_id):
    resp = api_get_request("reportreader_api", f"/report/{run_uuid}/{dataset_id}")
    catpile_resp = api_get_request(
        "catpile_api", f"/get_sp3_data_for_run_sample/{run_uuid}/{dataset_id}"
    )
    report_data = resp["report_data"]  # data in from catreport

    import reportlib

    template_report_data = reportlib.process_reports(
        report_data, catpile_resp, cfg.get("download_url")
    )
    template_report_data["run_uuid"] = run_uuid
    template_report_data["dataset_id"] = dataset_id

    jf = f"/tmp/{run_uuid}_{dataset_id}_report.json"
    rf = f"/tmp/{run_uuid}_{dataset_id}_report.pdf"
    with open(jf, "w") as f:
        f.write(json.dumps(template_report_data))
    brand_arg = f"--brand={current_user.get_org_name()}"
    cmd = f"/home/ubuntu/env/bin/python /home/ubuntu/sp3/catdoc/catdoc.py {shlex.quote(jf)} {shlex.quote(rf)} {shlex.quote(brand_arg)}"
    logging.warning(cmd)
    os.system(cmd)
    return send_file(rf, as_attachment=True, mimetype="application/pdf")


@app.route("/flow/<run_uuid>/<dataset_id>/report")
@flask_login.login_required
def get_report(run_uuid, dataset_id):
    resp = api_get_request("reportreader_api", f"/report/{run_uuid}/{dataset_id}")
    catpile_resp = api_get_request(
        "catpile_api", f"/get_sp3_data_for_run_sample/{run_uuid}/{dataset_id}"
    )
    report_data = resp["report_data"]  # data in from catreport

    import reportlib

    template_report_data = reportlib.process_reports(
        report_data, catpile_resp, cfg.get("download_url")
    )
    template_report_data["run_uuid"] = run_uuid
    template_report_data["dataset_id"] = dataset_id

    if request.args.get("api"):
        return json.dumps(template_report_data)

    return render_template(
        "report.template",
        sel="Runs/Outputs",
        list=list,
        pipeline_run_uuid=run_uuid,
        dataset_id=dataset_id,
        report=template_report_data,
    )


@app.route("/flow/<run_uuid>/<dataset_id>/report/data/<report_type>")
@flask_login.login_required
def get_report_raw_data(run_uuid, dataset_id, report_type):
    resp = api_get_request("reportreader_api", f"/report/{run_uuid}/{dataset_id}")
    catpile_resp = api_get_request(
        "catpile_api", f"/get_sp3_data_for_run_sample/{run_uuid}/{dataset_id}"
    )
    report_data = resp["report_data"]  # data in from catreport

    import reportlib

    template_report_data = reportlib.process_reports(
        report_data, catpile_resp, cfg.get("download_url")
    )

    if (
        report_type not in template_report_data
        or "raw_data" not in template_report_data[report_type]
    ):
        return abort(404)

    raw_data = template_report_data[report_type]["raw_data"]

    if report_type == "resistance":
        raw_data = json.dumps(json.loads(raw_data), indent=4)

    return render_template(
        "report_raw_data.template", sel="Runs/Outputs", raw_data=raw_data
    )


@app.route("/make_a_tree", methods=["POST"])
@flask_login.login_required
def make_a_tree():
    run_ids_sample_names = json.dumps(list(request.form.keys()))
    run_names_sample_names = list(request.form.values())
    logging.warning(f"tree requests: {request.form}")
    return render_template(
        "make_a_tree.template",
        sel="Trees",
        run_names_sample_names=run_names_sample_names,
        run_ids_sample_names=run_ids_sample_names,
    )


@app.route("/list_trees")
@flask_login.login_required
def list_trees():
    pipeline_run_uuid = request.args.get("pipeline_run_uuid")
    sample_name = request.args.get("sample_name")
    if pipeline_run_uuid and sample_name:
        trees = requests.get(
            "https://persistence.mmmoxford.uk/api_list_trees",
            params={"pipeline_run_uuid": pipeline_run_uuid, "sample_name": sample_name},
        ).json()
    else:
        trees = requests.get("https://persistence.mmmoxford.uk/api_list_trees").json()
    return render_template(
        "list_trees.template",
        sel="Trees",
        trees=trees,
        strftime=time.strftime,
        localtime=time.localtime,
        pipeline_run_uuid=pipeline_run_uuid,
        sample_name=sample_name,
    )


@app.route("/submit_tree", methods=["POST"])
@flask_login.login_required
def submit_tree():
    run_ids_sample_names = request.form.get("run_ids_sample_names")
    my_tree_name = request.form.get("my_tree_name")
    u = current_user
    logging.warning(f"run ids sample names: {run_ids_sample_names}")
    requests.post(
        "https://persistence.mmmoxford.uk/api_submit_tree",
        json={
            "my_tree_name": my_tree_name,
            "run_ids_sample_names": run_ids_sample_names,
            "provider": "iqtree1",
            "user": current_user.id,
            "org": current_user.get_org_name(),
        },
    )
    return redirect("/list_trees")


@app.route("/view_tree/<guid>")
@flask_login.login_required
def view_tree(guid):
    data = requests.get(
        f"https://persistence.mmmoxford.uk/api_get_tree/{ guid }"
    ).json()
    logging.warning(data)
    try:
        runs_names_map = requests.get(
            f"https://persistence.mmmoxford.uk/api_get_runs_name_map"
        ).json()
    except:
        runs_names_map = dict()
        pass

    result = json.loads(data["results"])
    tree_nwk = result["data"]["newick_content"]

    if runs_names_map:
        # rename tree nodes from "run-uuid_sample_name" to "sample name [run name]"
        import newick

        xs = newick.loads(tree_nwk)
        for tree in xs:
            for node in tree.walk():
                if node.name:
                    pipeline_run_uuid = node.name[0:36]
                    sample_name = node.name[37:]
                    if pipeline_run_uuid in runs_names_map:
                        node.name = f"{sample_name} [{runs_names_map[pipeline_run_uuid]['run_name']}]"
        tree_nwk = newick.dumps(xs)

    return render_template(
        "view_tree.template",
        sel="Trees",
        tree_nwk=tree_nwk,
        data=data,
        data2=json.loads(data["results"]),
    )


@app.route("/cw_query")
@flask_login.login_required
def cw_query():
    msg = ""
    all_runs = dict()
    neighbours = list()

    run_id = request.args.get("run_id")
    sample_name = request.args.get("sample_name")
    logging.debug(f"cw_query begin: sample_name: {sample_name}")
    distance = request.args.get("distance")
    neighbours_ok = False

    if not (run_id and sample_name and distance):
        return render_template("cw_query.template", sel="Trees", distance=12)

    else:
        # call persistence API to get run-name map
        if distance == "-1":
            import nifty_fifty

            res = json.dumps(
                nifty_fifty.nifty_neighbours(run_id, sample_name, trim=True)
            )
        else:
            combine_name = run_id + "_" + sample_name
            res = requests.get(
                f"https://persistence.mmmoxford.uk/api_cw_get_neighbours/{combine_name}/{distance}"
            ).text
        message = res
        logging.debug(f"catwalk returned: {res}")
        unique_samples = set()
        unique_neighbours = list()
        try:
            neighbours = json.loads(res)
            for neighbour in neighbours:
                neighbour_name = neighbour[0][37:]
                if neighbour_name not in unique_samples:
                    unique_samples.add(neighbour_name)
                    unique_neighbours.append(neighbour)
            neighbours_ok = True
            all_runs = requests.get(
                f"https://persistence.mmmoxford.uk/api_get_runs_name_map"
            ).json()
            message = ""
        except:
            pass
        logging.debug(f"cw_query end: sample_name: {sample_name}")
        return render_template(
            "cw_query.template",
            sel="Trees",
            neighbours_ok=neighbours_ok,
            all_runs=all_runs,
            run_id=run_id,
            sample_name=sample_name,
            distance=distance,
            message=message,
            neighbours=unique_neighbours,
        )


@app.route("/list_reports")
@flask_login.login_required
def list_reports():
    reports = api_get_request("reportreader_api", "/list_reports")
    return render_template(
        "list_reports.template",
        sel="Runs/Outputs",
        int=int,
        strftime=time.strftime,
        localtime=time.localtime,
        reports=reports,
    )


@app.route("/get_cluster_stats")
@flask_login.login_required
def proxy_get_cluster_stats():
    response = api_get_request("catstat_api", "/data")
    return json.dumps(response)


@app.route("/search")
@flask_login.login_required
def search_for_input_sample():
    sample_part = request.args.get("q", "")
    runs = list()
    message = None
    if sample_part:
        ret = db.search_for_input_sample(
            sample_part, current_user.get_org_name(), is_admin=current_user.is_admin()
        )
        if type(ret) == str:
            message = ret
        else:
            runs = ret

    return render_template(
        "search.template",
        sample_part=sample_part,
        message=message,
        runs=runs,
        sel="Search",
    )


#
# catforum integration
#
con = sqlite3.connect("/db/catforum.sqlite", check_same_thread=False)
con.row_factory = sqlite3.Row
con.execute(
    "create table if not exists post (id integer primary key autoincrement, status, parent_id integer, title, posted integer, edited integer, replied integer, replies_count integer, username, content)"
)
con.commit()


def send_email(recipients, subject, body):
    logging.warning(f"{recipients}, {subject}, {body}")
    if type(recipients) != list:
        recipients = [recipients]
    recipients = shlex.quote(",".join(recipients))
    subject = shlex.quote(subject)
    body = shlex.quote(body)
    cmd = f"python3 ./emails.py send-email-notification-multiple {recipients} {subject} {body} &"
    os.system(cmd)


def get_users():
    return requests.get("http://localhost:13666/get_users").json()


def get_users_on_post(post_id):
    poster = [
        x[0]
        for x in con.execute(
            "select username from post where id = ?", (post_id,)
        ).fetchall()
    ]
    reply_usernames = [
        x[0]
        for x in con.execute(
            "select username from post where parent_id = ?", (post_id,)
        ).fetchall()
    ]
    return poster + reply_usernames


def forum_email_new_reply_notification(reply_id):
    if not cfg.get("my_url"):
        logging.error(
            "config key my_url is not present. Can't set forum reply notifications. Add the key and set is to the base url of the site you're using if you want to send forum and run notifications"
        )
        return
    reply_username, parent_id = con.execute(
        "select username, parent_id from post where id = ?", (reply_id,)
    ).fetchall()[0]
    users_on_post = list(set(get_users_on_post(parent_id)))
    users_to_email = users_on_post[:]
    users_to_email.remove(reply_username)

    us = get_users()
    users_email_addrs = list()
    for u in users_to_email:
        if u in us and "attributes" in us[u] and "email" in us[u]["attributes"]:
            if "no_emails" in us[u]["attributes"]:
                continue
            users_email_addrs.append(us[u]["attributes"]["email"])

    subject = f"SP3 forum reply notification for post id { parent_id }"
    body = f"""Dear SP3 user

User { reply_username } posted a reply on a topic that you replied to:

{ cfg.get('my_url') }/post/{ parent_id }

If you'd rather not receive forum reply notifications, please email denis.volk@ndm.ox.ac.uk stating this.
"""
    send_email(users_email_addrs, subject, body)


# load post templates
post_templates = dict()


def load_post_templates():
    for template_path in pathlib.Path("forum_post_templates").glob("*.txt"):
        post_templates[template_path.stem] = open(template_path).read()


load_post_templates()


def text_to_html(text):
    pattern = (
        r"((([A-Za-z]{3,9}:(?:\/\/)?)"  # scheme
        r"(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:\[0-9]+)?"  # user@hostname:port
        r"|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)"  # www.|user@hostname
        r"((?:\/[\+~%\/\.\w\-_]*)?"  # path
        r"\??(?:[\-\+=&;%@\.\w_]*)"  # query parameters
        r"#?(?:[\.\!\/\\\w]*))?)"  # fragment
        r"(?![^<]*?(?:<\/\w+>|\/?>))"  # ignore anchor HTML tags
        r"(?![^\(]*?\))"  # ignore links in brackets (Markdown links and images)
    )
    link_patterns = [
        (re.compile(pattern), r"\1"),
        (re.compile("post\s+(\d+)(#\d+)", re.I), r"/post/\1\2"),
        (re.compile("post\s+(\d+)", re.I), r"/post/\1"),
    ]

    return markdown2.markdown(
        html.escape(text),
        extras=[
            "link-patterns",
            "wiki-tables",
            "task_list",
            "code-friendly",
            "cuddled-lists",
            "fenced-code-blocks",
            "break-on-newline",
        ],
        link_patterns=link_patterns,
    )


stat_in_cache = 0
stat_missed_cache = 0
html_cache = dict()


def post_to_html(post):
    global stat_in_cache
    global stat_missed_cache
    key = f"{post['id']}^{post['edited']}"
    print(key)
    if key in html_cache:
        stat_in_cache += 1
        return html_cache[key]
    else:
        stat_missed_cache += 1
        html = text_to_html(post["content"])
        html_cache[key] = html
        return html


@app.route("/forum")
@flask_login.login_required
def index():
    print(f"stat_in_cache={stat_in_cache}, stat_missed_cache={stat_missed_cache}")
    posts = con.execute(
        "select * from post where parent_id = -1 order by replied desc"
    ).fetchall()
    return render_template(
        "forum/index.template",
        title="Discussion Index",
        posts=posts,
        post_to_html=post_to_html,
        timefmt=timefmt,
        datefmt=datefmt,
        u=flask_login.current_user,
        sel="Forum",
    )


@app.route("/forum/post/edit/<edit_id>")
@flask_login.login_required
def post_edit(edit_id):
    post = con.execute("select * from post where id = ?", (edit_id,)).fetchone()
    if flask_login.current_user.id != post["username"]:
        return redirect("/forum")

    post_uuid = request.args.get("post_uuid", "")
    title, content = db.forum_get_post_cache(post_uuid)

    return render_template(
        "forum/make_new_post.template",
        parent_id=post["parent_id"],
        edit_id=edit_id,
        title=title,
        content=content,
        u=flask_login.current_user,
        sel="Forum",
    )


@app.route("/forum/post/new")
@flask_login.login_required
def post_new():
    post_uuid = request.args.get("post_uuid", "")
    title, content = db.forum_get_post_cache(post_uuid)

    post_template_name = request.args.get("post_template")
    if post_template_name:
        content = post_templates.get(post_template_name)
        if content:
            title = post_template_name.capitalize() + ": "

    return render_template(
        "forum/make_new_post.template",
        parent_id=-1,
        edit_id="",
        title=title,
        u=flask_login.current_user,
        content=content,
        template_names=list(post_templates.keys()),
        sel="Forum",
    )


@app.route("/forum/post/delete/<post_id>")
@flask_login.login_required
def post_delete(post_id):
    post = con.execute("select * from post where id = ?", (post_id,)).fetchone()
    if post["status"] == "deleted":
        return redirect("/forum")
    with con:
        con.execute(
            "update post set status='deleted' where id = ? and username = ?",
            (post_id, flask_login.current_user.id),
        )
        if post["parent_id"] != -1:
            con.execute(
                "update post set replies_count = replies_count - 1 where id = ?",
                (post["parent_id"],),
            )
    return redirect("/forum")


@app.route("/forum/post/<post_id>")
@flask_login.login_required
def post(post_id):
    post = con.execute("select * from post where id = ?", (post_id,)).fetchone()
    if not post:
        return redirect("/forum")
    replies = con.execute(
        "select * from post where parent_id = ?", (post_id,)
    ).fetchall()

    post_uuid = request.args.get("post_uuid", "")
    title, content = db.forum_get_post_cache(post_uuid)

    return render_template(
        "forum/post.template",
        post=post,
        replies=replies,
        parent_id=post_id,
        post_to_html=post_to_html,
        timefmt=timefmt,
        u=flask_login.current_user,
        title="Discussion Posts",
        content=content,
        sel="Forum",
    )


@app.route("/forum/new_post", methods=["POST"])
@flask_login.login_required
def new_post():
    if request.method == "POST":
        now = int(time.time())
        parent_id = request.form.get("parent_id", "-1")
        edit_id = request.form.get("edit_id")
        title = request.form.get("title", "no title")
        username = flask_login.current_user.id
        content = request.form.get("content", "no text")

        if request.form.get("preview"):
            post_uuid = db.forum_set_post_cache(title, content)
            return render_template(
                "forum/preview_post.template",
                parent_id=parent_id,
                title=title,
                content=content,
                u=flask_login.current_user,
                text_to_html=text_to_html,
                post_uuid=post_uuid,
                edit_id=edit_id,
                sel="Forum",
            )

        with con:
            if edit_id:
                con.execute(
                    "update post set title = ?, content = ?, edited = ? where id = ? and username = ?",
                    (title, content, now, edit_id, username),
                )
                new_post_id = edit_id
            else:
                con.execute(
                    "insert into post values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (None, "", parent_id, title, now, now, 0, 0, username, content),
                )
                new_post_id = con.execute(
                    "select id from post where title = ? and posted = ?", (title, now)
                ).fetchone()[0]
                if parent_id == "-1":
                    con.execute(
                        "update post set edited = ?, replied = ? where id = ?",
                        (now, now, new_post_id),
                    )
                else:
                    con.execute(
                        "update post set replied = ?, replies_count = replies_count + 1 where id = ?",
                        (
                            now,
                            parent_id,
                        ),
                    )

        # save the post to posts/
        # may be used to provide a post history later
        pathlib.Path("./forum_posts").mkdir(parents=True, exist_ok=True)
        with open(f"./forum_posts/{now}_{new_post_id}.json", "w") as f:
            f.write(
                json.dumps(
                    {
                        "now": now,
                        "parent_id": parent_id,
                        "edit_id": edit_id,
                        "title": title,
                        "username": username,
                        "content": content,
                        "req_headers": dict(request.headers),
                    },
                    indent=4,
                )
            )

        if parent_id == "-1":
            return redirect(f"/forum/post/{ new_post_id }")
        else:
            # forum_email_new_reply_notification(new_post_id)
            return redirect(f"/forum/post/{ parent_id }")


def main(port_=7000):
    global port
    port = port_

    reload_cfg()

    if cfg.get("sentry_io_url"):
        sentry_sdk.init(
            cfg.get("sentry_io_url"),
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.01,
        )

    waitress.serve(app, listen=f"127.0.0.1:{port}")


if __name__ == "__main__":
    argh.dispatch_command(main)
