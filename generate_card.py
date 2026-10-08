#!/usr/bin/env python3
import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

USER_ID = os.getenv("STACKALYTICS_USER", "sakumbha")
BASE = os.getenv("STACKALYTICS_BASE", "https://www.stackalytics.io")
OUT = Path("card.svg")


def get_json(path, params):
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "openstack-stats-card/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def esc(value):
    return html.escape(str(value), quote=True)


def fmt(value):
    try:
        n = float(value)
        if n.is_integer():
            return str(int(n))
        return f"{n:.1f}"
    except Exception:
        return "0"


def main():
    params = {
        "release": "all",
        "metric": "person-day",
        "project_type": "openstack",
        "user_id": USER_ID,
    }
    data = get_json("/api/1.0/stats/modules", params)
    rows = data.get("stats", [])

    values = {}
    for row in rows:
        name = row.get("name") or row.get("id") or ""
        try:
            values[name.lower()] = float(row.get("metric", 0))
        except (TypeError, ValueError):
            pass

    glance = values.get("glance", 0.0)
    manila = values.get("manila", 0.0)
    total = sum(values.values())
    shown = glance + manila
    other = max(total - shown, 0.0)

    if total <= 0:
        glance_pct = manila_pct = 0
    else:
        glance_pct = round(glance / total * 100)
        manila_pct = round(manila / total * 100)

    # Card dimensions are intentionally compact for a GitHub profile README.
    W, H = 980, 300
    bar_max = 420
    glance_w = int(bar_max * (glance / max(max(glance, manila), 1)))
    manila_w = int(bar_max * (manila / max(max(glance, manila), 1)))

    stats_url = f"https://www.stackalytics.io/?user_id={urllib.parse.quote(USER_ID)}&metric=person-day"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
  <title id="title">OpenStack contribution statistics for {esc(USER_ID)}</title>
  <desc id="desc">Stackalytics person-day contribution statistics, including Glance and Manila.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0d1117"/>
      <stop offset="1" stop-color="#111827"/>
    </linearGradient>
    <linearGradient id="blue" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#2f81f7"/>
      <stop offset="1" stop-color="#58a6ff"/>
    </linearGradient>
    <linearGradient id="green" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#2ea043"/>
      <stop offset="1" stop-color="#56d364"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="978" height="298" rx="18" fill="url(#bg)" stroke="#30363d" stroke-width="2"/>

  <!-- Header -->
  <rect x="28" y="28" width="58" height="58" rx="14" fill="#fff"/>
  <text x="57" y="64" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="28" font-weight="700" fill="#da2b4d">S</text>
  <text x="104" y="52" font-family="Arial,Helvetica,sans-serif" font-size="23" font-weight="700" fill="#f0f6fc">OpenStack Contributor</text>
  <text x="104" y="77" font-family="Arial,Helvetica,sans-serif" font-size="15" fill="#8b949e">Stackalytics · {esc(USER_ID)}</text>
  <rect x="816" y="35" width="126" height="34" rx="17" fill="#0d3b20" stroke="#238636"/>
  <text x="879" y="58" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="14" font-weight="700" fill="#56d364">↗ Upstream</text>

  <!-- Left metric -->
  <text x="32" y="135" font-family="Arial,Helvetica,sans-serif" font-size="14" fill="#8b949e">TOTAL PERSON-DAYS</text>
  <text x="32" y="188" font-family="Arial,Helvetica,sans-serif" font-size="52" font-weight="700" fill="#f0f6fc">{fmt(total)}</text>
  <text x="34" y="214" font-family="Arial,Helvetica,sans-serif" font-size="14" fill="#8b949e">OpenStack contribution activity</text>
  <text x="34" y="255" font-family="Arial,Helvetica,sans-serif" font-size="14" font-weight="600" fill="#c9d1d9">Glance → Manila</text>

  <line x1="300" y1="106" x2="300" y2="268" stroke="#30363d"/>

  <!-- Projects -->
  <text x="330" y="135" font-family="Arial,Helvetica,sans-serif" font-size="14" fill="#8b949e">CONTRIBUTIONS BY PROJECT</text>

  <text x="330" y="169" font-family="Arial,Helvetica,sans-serif" font-size="16" font-weight="700" fill="#f0f6fc">Glance</text>
  <text x="900" y="169" text-anchor="end" font-family="Arial,Helvetica,sans-serif" font-size="16" font-weight="700" fill="#f0f6fc">{fmt(glance)}</text>
  <rect x="330" y="181" width="570" height="12" rx="6" fill="#21262d"/>
  <rect x="330" y="181" width="{glance_w}" height="12" rx="6" fill="url(#blue)"/>
  <text x="914" y="191" font-family="Arial,Helvetica,sans-serif" font-size="12" fill="#8b949e">{glance_pct}%</text>

  <text x="330" y="226" font-family="Arial,Helvetica,sans-serif" font-size="16" font-weight="700" fill="#f0f6fc">Manila</text>
  <text x="900" y="226" text-anchor="end" font-family="Arial,Helvetica,sans-serif" font-size="16" font-weight="700" fill="#f0f6fc">{fmt(manila)}</text>
  <rect x="330" y="238" width="570" height="12" rx="6" fill="#21262d"/>
  <rect x="330" y="238" width="{manila_w}" height="12" rx="6" fill="url(#green)"/>
  <text x="914" y="248" font-family="Arial,Helvetica,sans-serif" font-size="12" fill="#8b949e">{manila_pct}%</text>

  <a href="{esc(stats_url)}">
    <rect x="690" y="262" width="250" height="28" rx="14" fill="none" stroke="#484f58"/>
    <text x="815" y="281" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="13" font-weight="600" fill="#c9d1d9">View full Stackalytics stats ↗</text>
  </a>

  <!-- Tiny note -->
  <text x="32" y="285" font-family="Arial,Helvetica,sans-serif" font-size="10" fill="#6e7681">Data: Stackalytics · updated by GitHub Actions</text>
</svg>
'''
    OUT.write_text(svg, encoding="utf-8")
    print(f"Generated {OUT}: total={total:.2f}, glance={glance:.2f}, manila={manila:.2f}, other={other:.2f}")


if __name__ == "__main__":
    main()
