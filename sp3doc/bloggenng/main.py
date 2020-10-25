import os
import markdown2
from bs4 import BeautifulSoup as BS
import pathlib

header = open('header.html').read()
footer = open('footer.html').read()

post_paths = list(pathlib.Path("./posts").glob("*.md"))
post_paths.sort(key=os.path.getctime, reverse=True)

posts = list()
for post_path in post_paths:
    md_html = markdown2.markdown(open(post_path).read())
    soup = BS(md_html, features="lxml")
    post_out = BS(header + str(soup) + footer, features="lxml")
    post_out.html.head.insert(0, BS(f'<title>{ post_out.h2.text }</title>', features="lxml").html.head.title)
    post_out.h1.replaceWith(BS(f'<h1><a href="index.html">{ post_out.h1.text }</a></h1>', features="lxml").body.next)
    post_out.h2.replaceWith(BS(f'<h2><a href="./{ post_path.stem }.html">{ soup.h2.text }</a></h2>', features="lxml").body.next)
    out_path = f"posts/{ post_path.stem }.html"
    open(out_path, "w").write(str(post_out))
    soup.h2.replaceWith(BS(f'<h2><a href="./{ post_path.stem }.html">{ soup.h2.text }</a></h2>', features="lxml").body.next)
    posts.append(soup.prettify())

soup = BS(header + "".join(posts) + footer, features="lxml")
soup.html.head.insert(0, BS(f'<title>{ soup.h1.text }</title>', features="lxml").html.head.title)
soup.h1.replaceWith(BS(f'<h1><a href="./index.html">{ soup.h1.text }</a></h1>', features="lxml").body.next)
print(soup.prettify())
