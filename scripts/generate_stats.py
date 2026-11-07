"""Generate assets/stats.svg: most-used languages across a user's public, non-fork repositories.

Uses only the Python standard library and the public GitHub REST API.
Usage: python scripts/generate_stats.py omnagpure [output.svg]
Set GITHUB_TOKEN to avoid the unauthenticated rate limit.
"""
import json
import os
import sys
import urllib.request
from html import escape

MONO = "ui-monospace,'SF Mono','JetBrains Mono',Consolas,'Courier New',monospace"
SANS = "'Inter','Segoe UI',system-ui,-apple-system,Helvetica,Arial,sans-serif"
TEAL = "#2DD4BF"
SHADES = ["#2DD4BF", "#14B8A6", "#5EEAD4", "#0D9488", "#99F6E4", "#475569"]
MAX_LANGS = 6
# Notebook file size includes saved outputs and inflates the share, so it is left out.
EXCLUDE = {"Jupyter Notebook"}


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect(user):
    repos, page = [], 1
    while True:
        batch = get(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    totals = {}
    for r in own:
        for lang, n in get(r["languages_url"]).items():
            if lang in EXCLUDE:
                continue
            totals[lang] = totals.get(lang, 0) + n
    return len(own), totals


def render(user, repo_count, totals):
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(n for _, n in ranked) or 1
    top = ranked[:MAX_LANGS]
    rest = sum(n for _, n in ranked[MAX_LANGS:])
    if rest:
        top.append(("Other", rest))
    colors = [SHADES[i % (len(SHADES) - 1)] for i in range(len(top))]
    if rest:
        colors[-1] = SHADES[-1]

    rows = max(1, -(-len(top) // 3))
    w, h, x0, bar_w = 900, 140 + (rows - 1) * 32 + 40, 48, 804
    out = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">
  <title id="t">Most used languages</title>
  <desc id="d">{escape(", ".join(f"{k} {v*100/total:.0f}%" for k, v in top)) or "No language data yet"} across {repo_count} public repositories by {escape(user)}.</desc>
  <defs>
    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#131A22" stroke-width="1"/></pattern>
    <clipPath id="bar"><rect x="{x0}" y="92" width="{bar_w}" height="12" rx="6"/></clipPath>
  </defs>
  <rect width="{w}" height="{h}" rx="16" fill="#0B0F14"/>
  <rect width="{w}" height="{h}" rx="16" fill="url(#grid)"/>
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="16" fill="none" stroke="#1B2430"/>
  <rect x="{x0}" y="40" width="28" height="3" fill="{TEAL}"/>
  <text x="{x0}" y="72" font-family="{MONO}" font-size="13" letter-spacing="3" fill="{TEAL}">MOST USED LANGUAGES</text>
  <text x="{w-x0}" y="72" text-anchor="end" font-family="{MONO}" font-size="13" fill="#5B6773">{repo_count} public repositories</text>
''']
    if not top:
        out.append(f'  <text x="{x0}" y="130" font-family="{SANS}" font-size="16" fill="#8B98A5">No language data yet.</text>\n</svg>\n')
        return "".join(out)

    x = float(x0)
    out.append('  <g clip-path="url(#bar)">\n')
    for i, (name, n) in enumerate(top):
        seg = bar_w * n / total
        out.append(f'    <rect x="{x:.1f}" y="92" width="{seg+0.5:.1f}" height="12" fill="{colors[i]}"/>\n')
        x += seg
    out.append('  </g>\n')

    cols = 3
    for i, (name, n) in enumerate(top):
        cx = x0 + (i % cols) * 270
        cy = 140 + (i // cols) * 32
        out.append(f'  <circle cx="{cx+5}" cy="{cy-5}" r="5" fill="{colors[i]}"/>\n')
        out.append(f'  <text x="{cx+18}" y="{cy}" font-family="{SANS}" font-size="16" font-weight="600" fill="#E6EDF3">{escape(name)}</text>\n')
        out.append(f'  <text x="{cx+18+len(name)*10.5+12:.0f}" y="{cy}" font-family="{MONO}" font-size="14" fill="#8B98A5">{n*100/total:.1f}%</text>\n')
    out.append("</svg>\n")
    return "".join(out)


if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "omnagpure"
    dest = sys.argv[2] if len(sys.argv) > 2 else "assets/stats.svg"
    count, totals = collect(user)
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(render(user, count, totals))
    print(f"{user}: {count} repos, languages: {dict(sorted(totals.items(), key=lambda kv: -kv[1]))}")
