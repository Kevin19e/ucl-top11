"""Build index.html (the GitHub Pages site) from ucl-top11.html (the page source).

ucl-top11.html is written as a page fragment: <title>, font <link>, <style>, markup, scripts.
This wraps it in a full HTML document. Run after every data update:  python build.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
src = (ROOT / "ucl-top11.html").read_text(encoding="utf-8")

title = re.search(r"<title>.*?</title>", src, re.S)
link = re.search(r'<link rel="stylesheet"[^>]*>', src)
body = src
for m in (title, link):
    if m:
        body = body.replace(m.group(0), "", 1)

head = "\n".join([
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
    '<meta name="description" content="A first and second XI by position for each Champions League matchday: '
    'who is most likely to score, assist or keep a clean sheet.">',
    title.group(0) if title else "<title>UCL Top 11</title>",
    link.group(0) if link else "",
    "<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>",
])

out = f'<!doctype html>\n<html lang="en">\n<head>\n{head}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n'
(ROOT / "index.html").write_text(out, encoding="utf-8")
print(f"index.html written ({len(out):,} bytes)")
