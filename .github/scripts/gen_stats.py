#!/usr/bin/env python3
"""Generate terminal-style stats SVGs (light + dark) into dist/."""
import datetime
import json
import os
import urllib.request

API = "https://api.github.com"
USER = "ltspace"
TOKEN = os.environ["GITHUB_TOKEN"]


def get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": USER,
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def bar(frac, width=10):
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)


user = get(f"{API}/users/{USER}")
repos = get(f"{API}/users/{USER}/repos?per_page=100")
own = [r for r in repos if not r["fork"]]
stars = sum(r["stargazers_count"] for r in own)

langs = {}
for r in own:
    for lang, n in get(r["languages_url"]).items():
        langs[lang] = langs.get(lang, 0) + n
total = sum(langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: -kv[1])[:4]

year = datetime.date.today().year
commits = get(
    f"{API}/search/commits?q=author:{USER}+author-date:%3E%3D{year}-01-01"
)["total_count"]

# each line is a list of (text, role) segments; role picks the color
lines = [
    [(f"{USER}@github", "accent"), (":~$ ", "dim"), ("fetch --profile", "fg")],
    [],
    [("  user      ", "dim"), (f'{user["name"]} (@{USER})', "fg")],
    [("  repos     ", "dim"),
     (f'{user["public_repos"]} public · {len(own)} original', "fg")],
    [("  stars     ", "dim"), (f"★ {stars}", "fg")],
    [("  commits   ", "dim"), (f"{commits} in {year}", "fg")],
    [("  followers ", "dim"), (str(user["followers"]), "fg")],
    [],
]
for i, (lang, n) in enumerate(top):
    label = "  langs     " if i == 0 else "            "
    lines.append([
        (label, "dim"),
        (f"{lang:<12}", "fg"),
        (bar(n / total), "dim"),
        (f" {n / total * 100:5.1f}%", "fg"),
    ])
lines += [
    [],
    [(f"{USER}@github", "accent"), (":~$ ", "dim"), ("█", "fg")],
]

PALETTES = {
    "stats.svg": {
        "bg": "#ffffff", "border": "#d0d7de",
        "fg": "#24292f", "dim": "#6e7781", "accent": "#24292f",
    },
    "stats-dark.svg": {
        "bg": "#0d1117", "border": "#30363d",
        "fg": "#c9d1d9", "dim": "#8b949e", "accent": "#c9d1d9",
    },
}

LINE_H, PAD, FONT = 21, 18, 14
width = 520
height = PAD * 2 + LINE_H * len(lines)

os.makedirs("dist", exist_ok=True)
for name, p in PALETTES.items():
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, '
        f'\'Liberation Mono\', monospace" font-size="{FONT}" '
        f'xml:space="preserve">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" '
        f'rx="6" fill="{p["bg"]}" stroke="{p["border"]}"/>',
    ]
    y = PAD + FONT
    for segs in lines:
        if segs:
            spans = "".join(
                f'<tspan fill="{p[role]}">{esc(text)}</tspan>'
                for text, role in segs
            )
            out.append(f'<text x="{PAD}" y="{y}">{spans}</text>')
        y += LINE_H
    out.append("</svg>")
    with open(os.path.join("dist", name), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"wrote dist/{name}")
