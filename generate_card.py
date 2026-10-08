#!/usr/bin/env python3

import json
import os
import subprocess
import urllib.parse
from pathlib import Path


BASE = "https://www.stackalytics.io"
OUTPUT = Path("card.svg")

USER = os.environ.get("STACKALYTICS_USER", "sakumbha")

STACKALYTICS_URL = (
    f"{BASE}/?user_id={urllib.parse.quote(USER)}&metric=person-day"
)


def get_json(path, params):
    """Fetch JSON from Stackalytics."""
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"

    print(f"Fetching: {url}")

    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",

            # Stackalytics currently has a certificate-chain issue
            # that causes Ubuntu/GitHub Actions to reject the TLS chain.
            "--insecure",

            "--retry",
            "3",
            "--retry-delay",
            "2",
            "--user-agent",
            "openstack-stats-card/1.0",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Stackalytics returned invalid JSON:\n{result.stdout}"
        ) from exc


def get_project_stats():
    """Get OpenStack project person-day statistics."""
    data = get_json(
        "/api/1.0/stats/modules",
        {
            "release": "all",
            "metric": "person-day",
            "project_type": "openstack",
            "user_id": USER,
        },
    )

    stats = data.get("stats", [])

    projects = []

    for item in stats:
        name = item.get("name")
        metric = item.get("metric", 0)

        if not name:
            continue

        try:
            metric = float(metric)
        except (TypeError, ValueError):
            continue

        projects.append(
            {
                "name": name,
                "value": metric,
            }
        )

    projects.sort(key=lambda x: x["value"], reverse=True)

    return projects


def format_number(value):
    """Format a number cleanly."""
    if value == int(value):
        return str(int(value))

    return f"{value:.1f}"


def make_bar(
    svg,
    x,
    y,
    width,
    height,
    value,
    max_value,
    label,
    color="#e01b24",
):
    """Add a project bar to the SVG."""

    # Background
    svg.append(
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="6" fill="#30363d"/>'
    )

    # Filled bar
    if max_value > 0:
        fill_width = max(4, width * value / max_value)
    else:
        fill_width = 0

    svg.append(
        f'<rect x="{x}" y="{y}" width="{fill_width:.2f}" '
        f'height="{height}" rx="6" fill="{color}"/>'
    )

    # Label
    svg.append(
        f'<text x="{x}" y="{y - 10}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="16" font-weight="600" fill="#f0f6fc">'
        f'{label}</text>'
    )

    # Value
    svg.append(
        f'<text x="{x + width}" y="{y - 10}" text-anchor="end" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="15" fill="#8b949e">'
        f'{format_number(value)} person-days</text>'
    )


def build_svg(projects):
    """Build the contribution card SVG."""

    # ---------------------------------------------------------
    # Calculate totals
    # ---------------------------------------------------------

    total = sum(project["value"] for project in projects)

    glance = next(
        (p["value"] for p in projects if p["name"] == "glance"),
        0,
    )

    manila = next(
        (p["value"] for p in projects if p["name"] == "manila"),
        0,
    )

    # Everything other than Glance and Manila
    other = total - glance - manila

    # Avoid negative values due to unexpected API data
    other = max(0, other)

    # ---------------------------------------------------------
    # SVG setup
    # ---------------------------------------------------------

    width = 900
    height = 430

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
    ]

    # Background
    svg.append(
        f'<rect width="{width}" height="{height}" '
        f'rx="18" fill="#0d1117"/>'
    )

    # OpenStack red accent
    svg.append(
        '<rect x="0" y="0" width="8" height="430" '
        'rx="4" fill="#e01b24"/>'
    )

    # Subtle border
    svg.append(
        '<rect x="1" y="1" width="898" height="428" '
        'rx="18" fill="none" stroke="#30363d"/>'
    )

    # ---------------------------------------------------------
    # Header
    # ---------------------------------------------------------

    svg.append(
        '<text x="42" y="50" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="26" font-weight="700" fill="#f0f6fc">'
        'OpenStack Contributor</text>'
    )

    # Upstream badge
    svg.append(
        '<rect x="42" y="68" width="108" height="28" '
        'rx="14" fill="#21262d" stroke="#30363d"/>'
    )

    svg.append(
        '<text x="96" y="87" text-anchor="middle" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="13" font-weight="600" fill="#58a6ff">'
        'UPSTREAM</text>'
    )

    # Stackalytics username
    svg.append(
        f'<text x="170" y="87" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="14" fill="#8b949e">'
        f'Stackalytics · {USER}</text>'
    )

    # ---------------------------------------------------------
    # Main total
    # ---------------------------------------------------------

    svg.append(
        f'<text x="42" y="158" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="64" font-weight="700" fill="#ffffff">'
        f'{format_number(total)}</text>'
    )

    svg.append(
        '<text x="43" y="185" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="17" fill="#8b949e">'
        'person-days across OpenStack</text>'
    )

    # Glance → Manila transition
    svg.append(
        '<text x="42" y="218" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="15" fill="#58a6ff">'
        'Glance → Manila</text>'
    )

    svg.append(
        '<text x="165" y="218" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="15" fill="#8b949e">'
        'upstream contribution journey</text>'
    )

    # ---------------------------------------------------------
    # Project bars
    # ---------------------------------------------------------

    bar_x = 42
    bar_width = 816
    bar_height = 14

    # Only show these three groups
    rows = [
        ("Glance", glance),
        ("Manila", manila),
        ("Other OpenStack", other),
    ]

    max_value = max(value for _, value in rows)

    y = 270

    for label, value in rows:
        make_bar(
            svg=svg,
            x=bar_x,
            y=y,
            width=bar_width,
            height=bar_height,
            value=value,
            max_value=max_value,
            label=label,
        )

        y += 48

    # ---------------------------------------------------------
    # Footer
    # ---------------------------------------------------------

    svg.append(
        '<line x1="42" y1="405" x2="858" y2="405" '
        'stroke="#21262d"/>'
    )

    svg.append(
        f'<a href="{STACKALYTICS_URL}" target="_blank">'
        '<text x="42" y="420" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="12" fill="#8b949e">'
        'View full Stackalytics profile →'
        '</text>'
        '</a>'
    )

    svg.append("</svg>")

    return "\n".join(svg)


def main():
    print(f"Generating OpenStack contribution card for: {USER}")

    projects = get_project_stats()

    if not projects:
        raise RuntimeError(
            "No project statistics were returned by Stackalytics."
        )

    print("\nProject statistics:")

    for project in projects:
        print(
            f"  {project['name']}: "
            f"{format_number(project['value'])} person-days"
        )

    total = sum(project["value"] for project in projects)

    print(
        f"\nTotal: {format_number(total)} person-days"
    )

    svg = build_svg(projects)

    OUTPUT.write_text(svg, encoding="utf-8")

    print(f"\nCard written to: {OUTPUT}")


if __name__ == "__main__":
    main()
