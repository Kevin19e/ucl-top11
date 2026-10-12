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
    '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 36%27%3E'
    '%3Cg fill=%27none%27 stroke=%27%230C1433%27 stroke-width=%274.6%27 stroke-linecap=%27round%27%3E'
    '%3Cpath d=%27M9.5 7C2.5 5.5 1 14.5 6.5 18.5c2 1.4 4 .6 5-1%27/%3E%3Cpath d=%27M22.5 7c7-1.5 8.5 7.5 3 11.5-2 1.4-4 .6-5-1%27/%3E%3C/g%3E'
    '%3Cg fill=%27%23DDE3F5%27 stroke=%27%230C1433%27 stroke-width=%271.5%27 stroke-linejoin=%27round%27%3E'
    '%3Cpath d=%27M9 4.5h14c0 9.5-2.5 14.5-5 16.5v5h-4v-5c-2.5-2-5-7-5-16.5Z%27/%3E%3Cpath d=%27M11.5 26h9l2 5h-13Z%27/%3E'
    '%3Crect x=%277%27 y=%2731%27 width=%2718%27 height=%273%27 rx=%271%27/%3E%3C/g%3E%3C/svg%3E">',
    "<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>",
])

out = f'<!doctype html>\n<html lang="en">\n<head>\n{head}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n'
(ROOT / "index.html").write_text(out, encoding="utf-8")
print(f"index.html written ({len(out):,} bytes)")
