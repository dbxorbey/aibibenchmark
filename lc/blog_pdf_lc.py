"""Render blog/blog_post.md (with both SVG charts inlined) to blog/blog_post.pdf - same layout as ../blog_pdf.py.

Usage: python lc/chart_lc.py && python lc/blog_pdf_lc.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import markdown  # noqa: E402

from blog_pdf import CSS  # noqa: E402

CSS += "img { display: block; max-width: 70%; margin: 6pt auto 2pt; border: 1px solid #e1e0d9; border-radius: 6pt; }"
from chart import CHROME  # noqa: E402


def main():
    blog = os.path.join(HERE, "blog")
    md = open(os.path.join(blog, "blog_post.md")).read()
    md = re.sub(r"^((?:  )+)(?=- )", lambda m: m.group(1) * 2, md, flags=re.M)
    body = markdown.markdown(md, extensions=["tables"])
    # a PDF cannot animate: use the static screenshot instead of the scrolling GIF
    body = body.replace('src="dashboard.gif"', 'src="dashboard.png"')
    body = re.sub(r'<img alt="[^"]*" src="([\w_]+\.svg)" ?/?>',
                  lambda m: f'<div class="fig">{open(os.path.join(blog, m.group(1))).read()}</div>', body)
    html_path = os.path.join(blog, "blog_post_print.html")
    open(html_path, "w").write(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Blog post</title>'
                               f'<style>{CSS}</style></head><body>{body}</body></html>')
    out = os.path.join(blog, "blog_post.pdf")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out}",
                    "file://" + html_path], capture_output=True, check=True)
    os.remove(html_path)
    print(out)


if __name__ == "__main__":
    main()
