import sqlite3, json, uuid, time, re, os, html, pathlib, uuid, subprocess, shlex
from logging import warning as logging_warning

from flask import *
import flask_login
from werkzeug.urls import url_parse
import markdown2, argh, requests

con = sqlite3.connect("/db/catforum.sqlite", check_same_thread=False)
con.row_factory = sqlite3.Row
con.execute(
    "create table if not exists post (id integer primary key autoincrement, status, parent_id integer, title, posted integer, edited integer, replied integer, replies_count integer, username, content)"
)
con.commit()


def send_email(recipients, subject, body):
    logging_warning(f"{recipients}, {subject}, {body}")
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


def email_new_reply_notification(reply_id):
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

https://sp3forum.mmmoxford.uk/post/{ parent_id }

If you'd rather not receive forum reply notifications, please email denis.volk@ndm.ox.ac.uk stating this.
"""
    send_email(users_email_addrs, subject, body)


# load post templates
post_templates = dict()


def load_post_templates():
    for template_path in pathlib.Path("forum_post_templates").glob("*.txt"):
        post_templates[template_path.stem] = open(template_path).read()


load_post_templates()


def timefmt(epochtime):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(epochtime))


def datefmt(epochtime):
    return time.strftime("%Y-%m-%d", time.localtime(epochtime))


version = (
    subprocess.check_output(shlex.split("git describe --tags --always --dirty"))
    .decode()
    .strip()
)

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


def text_to_html(text):
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


app = Flask(__name__)
app.secret_key = "bleh"
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "/login"


@app.route("/forum")
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
        version=version,
    )


@app.route("/forum/post/edit/<edit_id>")
@flask_login.login_required
def post_edit(edit_id):
    post = con.execute("select * from post where id = ?", (edit_id,)).fetchone()
    if flask_login.current_user.id != post["username"]:
        return redirect("/forum")

    post_uuid = request.args.get("post_uuid")
    if post_uuid:
        c = post_cache.get(post_uuid)
        if c:
            title, content = c["title"], c["content"]
    else:
        title = post["title"]
        content = post["content"]

    return render_template(
        "forum/make_new_post.template",
        parent_id=post["parent_id"],
        edit_id=edit_id,
        title=title,
        content=content,
        u=flask_login.current_user,
        version=version,
    )


# post cache stores post previews, so you that when you go back to editing,
# it reloads your text
# previously the back button just used javascript to go back in history, but
# this didn't work with the post template feature added later
post_cache = dict()


@app.route("/forum/post/new")
@flask_login.login_required
def post_new():
    title, content = "", ""

    post_template_name = request.args.get("post_template")
    if post_template_name:
        content = post_templates.get(post_template_name)
        if content:
            title = post_template_name.capitalize() + ": "

    post_uuid = request.args.get("post_uuid")
    if post_uuid:
        c = post_cache.get(post_uuid)
        if c:
            title, content = c["title"], c["content"]

    return render_template(
        "forum/make_new_post.template",
        parent_id=-1,
        edit_id="",
        title=title,
        u=flask_login.current_user,
        content=content,
        template_names=list(post_templates.keys()),
        version=version,
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
def post(post_id):
    post = con.execute("select * from post where id = ?", (post_id,)).fetchone()
    if not post:
        return redirect("/forum")
    replies = con.execute(
        "select * from post where parent_id = ?", (post_id,)
    ).fetchall()

    title, content = "", ""
    post_uuid = request.args.get("post_uuid")
    if post_uuid:
        c = post_cache.get(post_uuid)
        if c:
            title, content = c["title"], c["content"]
    else:
        title = post["title"]
        content = post["content"]

    return render_template(
        "forum/post.template",
        post=post,
        replies=replies,
        parent_id=post_id,
        post_to_html=post_to_html,
        timefmt=timefmt,
        u=flask_login.current_user,
        version=version,
        title="Discussion Posts",
        content=content,
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
            post_uuid = str(uuid.uuid4())
            post_cache[post_uuid] = {"title": title, "content": content}
            return render_template(
                "forum/preview_post.template",
                parent_id=parent_id,
                title=title,
                content=content,
                u=flask_login.current_user,
                text_to_html=text_to_html,
                post_uuid=post_uuid,
                edit_id=edit_id,
                version=version,
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
                        (now, parent_id,),
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
            email_new_reply_notification(new_post_id)
            return redirect(f"/forum/post/{ parent_id }")


def main():
    app.run(port=8765, debug=True)


if __name__ == "__main__":
    main()
