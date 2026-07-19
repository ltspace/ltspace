#!/usr/bin/env python3
"""Refresh README stats and redraw the contribution pulsar artwork."""
import datetime
import json
import math
import os
import re
import urllib.request

API = "https://api.github.com"
USER = "ltspace"
TOKEN = os.environ["GITHUB_TOKEN"]

BEGIN = f"{USER}@github:~$ fetch --profile"
END = f"{USER}@github:~$ █"


def call(url, data=None):
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": USER,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def bar(frac, width=10):
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)


# ---------- stats section of README ----------
user = call(f"{API}/users/{USER}")
repos = call(f"{API}/users/{USER}/repos?per_page=100")
own = [r for r in repos if not r["fork"]]
stars = sum(r["stargazers_count"] for r in own)

langs = {}
for r in own:
    for lang, n in call(r["languages_url"]).items():
        langs[lang] = langs.get(lang, 0) + n
total = sum(langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: -kv[1])[:4]

year = datetime.date.today().year
commits = call(
    f"{API}/search/commits?q=author:{USER}+author-date:%3E%3D{year}-01-01"
)["total_count"]

lines = [
    f"repos      {user['public_repos']} public · {len(own)} original",
    f"stars      ★ {stars}",
    f"commits    {commits} in {year}",
    f"followers  {user['followers']}",
]
for i, (lang, n) in enumerate(top):
    label = "langs      " if i == 0 else "           "
    lines.append(f"{label}{lang:<9}{bar(n / total)}  {n / total * 100:4.1f}%")

block = BEGIN + "\n" + "\n".join(lines) + "\n\n" + END

with open("README.md", encoding="utf-8") as f:
    readme = f.read()
if BEGIN not in readme:
    raise SystemExit("anchor line not found in README.md")
readme = re.sub(
    re.escape(BEGIN) + ".*?" + re.escape(END),
    block, readme, count=1, flags=re.DOTALL,
)
with open("README.md", "w", encoding="utf-8", newline="\n") as f:
    f.write(readme)
print("README.md refreshed")

# ---------- pulsar artwork ----------
query = json.dumps({"query": """
query { user(login: "%s") { contributionsCollection {
  contributionCalendar { weeks { contributionDays { contributionCount } } }
} } }""" % USER}).encode()
weeks_raw = call(f"{API}/graphql", data=query)["data"]["user"][
    "contributionsCollection"]["contributionCalendar"]["weeks"]
weeks = [[d["contributionCount"] for d in w["contributionDays"]]
         for w in weeks_raw][-52:]
weeks = [w + [0] * (7 - len(w)) for w in weeks]
# drop the leading dormant stretch so the signal fills the frame
while len(weeks) > 12 and sum(weeks[0]) == 0:
    weeks.pop(0)
peak = max(1, max(c for w in weeks for c in w))

W = 440
X_PAD, X_FLAT = 24, 60          # outer edge / start of the wave band
TOP, BOTTOM = 60, 48
SPACING = min(16.0, (470 - TOP - BOTTOM) / max(len(weeks) - 1, 1))
AMP = min(60.0, SPACING * 4.5)
TEX = min(2.5, SPACING / 7.5)   # texture scales with line spacing
H = round(TOP + (len(weeks) - 1) * SPACING + BOTTOM)
SAMPLES = 64


def grain(row, i):
    return math.sin(row * 12.9898 + i * 78.233) * 43758.5453 % 1 - 0.5


def texture(row, i):
    # smooth low-frequency wobble so idle weeks still read as a signal
    return (math.sin(i * 0.11 + row * 3.1)
            + 0.5 * math.sin(i * 0.27 + row * 7.7)) * 1.1


def row_points(row, values, baseline):
    pts = [(X_PAD, baseline)]
    for i in range(SAMPLES + 1):
        t = i / SAMPLES
        pos = t * 6
        k = int(pos)
        c = (1 - math.cos((pos - k) * math.pi)) / 2
        val = values[k] * (1 - c) + values[min(k + 1, 6)] * c
        h = math.log1p(val) / math.log1p(peak) * AMP
        # taper peaks near the margins so they never hit the frame edge
        he = min(1.0, t / 0.14, (1 - t) / 0.14)
        h *= he * he * (3 - 2 * he)
        # fade the ambient texture near the flat margins
        edge = min(1.0, 6 * t, 6 * (1 - t))
        y = baseline - h + (texture(row, i) + grain(row, i) * 0.6) * edge * TEX
        x = X_FLAT + t * (W - 2 * X_FLAT)
        pts.append((x, y))
    pts.append((W - X_PAD, baseline))
    return pts


def render(path_out, bg, fg):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{bg}"/>',
    ]
    for row, values in enumerate(weeks):
        baseline = TOP + row * SPACING
        pts = row_points(row, values, baseline)
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        fill = d + f" L{W - X_PAD},{H} L{X_PAD},{H} Z"
        parts.append(f'<path d="{fill}" fill="{bg}" stroke="none"/>')
        parts.append(
            f'<path d="{d}" fill="none" stroke="{fg}" stroke-width="1" '
            f'stroke-linejoin="round"/>')
    parts.append("</svg>")
    with open(path_out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts))
    print(f"wrote {path_out}")


os.makedirs("assets", exist_ok=True)
render("assets/pulse.svg", "#ffffff", "#24292f")
render("assets/pulse-dark.svg", "#0d1117", "#c9d1d9")
