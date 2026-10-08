#!/usr/bin/env python3

import html
import json
import os
import subprocess
import urllib.parse
from pathlib import Path


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

BASE = "https://www.stackalytics.io"
OUTPUT = Path("card.svg")

USER = os.environ.get("STACKALYTICS_USER", "sakumbha")

# Stackalytics profile
STACKALYTICS_URL = (
    f"{BASE}/?user_id={urllib.parse.quote(USER)}"
    f"&metric=patches"
)


# ----------------------------------------------------------------------
# Stackalytics API
# ----------------------------------------------------------------------

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

            # Stackalytics currently has a certificate-chain
            # issue on GitHub Actions/Ubuntu.
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
            "Stackalytics returned invalid JSON:\n"
            f"{result.stdout}"
        ) from exc


def get_project_stats():
    """
    Get OpenStack patch-set statistics from Stackalytics.

    Stackalytics' 'patches' metric represents Patch Sets by Module.
    """

    data = get_json(
        "/api/1.0/stats/modules",
        {
            "release": "all",
            "metric": "patches",
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

    projects.sort(
        key=lambda project: project["value"],
        reverse=True,
    )

    return projects


# ----------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------

def fmt(value):
    """Format numbers cleanly."""

    if value == int(value):
        return str(int(value))

    return f"{value:.1f}"


def percentage(value, total):
    """Calculate percentage."""

    if total <= 0:
        return 0

    return (value / total) * 100


def esc(value):
    """Escape text for SVG/XML."""

    return html.escape(
        str(value),
        quote=True,
    )


# ----------------------------------------------------------------------
# SVG helpers
# ----------------------------------------------------------------------

def add_text(
    svg,
    x,
    y,
    content,
    size=16,
    color="#f0f6fc",
    weight="400",
    anchor="start",
):
    """Add text element."""

    svg.append(
        f'<text '
        f'x="{x}" '
        f'y="{y}" '
        f'text-anchor="{anchor}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" '
        f'font-weight="{weight}" '
        f'fill="{color}">'
        f'{esc(content)}'
        f'</text>'
    )


def add_rect(
    svg,
    x,
    y,
    width,
    height,
    fill,
    radius=10,
    stroke=None,
):
    """Add rounded rectangle."""

    stroke_attr = ""

    if stroke:
        stroke_attr = f' stroke="{stroke}"'

    svg.append(
        f'<rect '
        f'x="{x}" '
        f'y="{y}" '
        f'width="{width}" '
        f'height="{height}" '
        f'rx="{radius}" '
        f'fill="{fill}"'
        f'{stroke_attr}/>'
    )


def add_project_row(
    svg,
    name,
    value,
    total,
    x,
    y,
    width,
    color="#e01b24",
):
    """Add project name, patch count and progress bar."""

    percent = percentage(
        value,
        total,
    )

    # Project name
    add_text(
        svg,
        x,
        y,
        name,
        size=15,
        color="#f0f6fc",
        weight="700",
    )

    # Patch-set count
    add_text(
        svg,
        x + width,
        y,
        f"{fmt(value)} patch sets · {percent:.1f}%",
        size=14,
        color="#8b949e",
        anchor="end",
    )

    # Background bar
    bar_y = y + 13

    add_rect(
        svg,
        x,
        bar_y,
        width,
        10,
        "#30363d",
        radius=5,
    )

    # Filled bar
    if percent > 0:
        fill_width = width * percent / 100

        add_rect(
            svg,
            x,
            bar_y,
            max(5, fill_width),
            10,
            color,
            radius=5,
        )


# ----------------------------------------------------------------------
# SVG card
# ----------------------------------------------------------------------

def build_svg(projects):
    """Build the OpenStack contribution card."""

    # --------------------------------------------------------------
    # Find the two core projects
    # --------------------------------------------------------------

    glance = next(
        (
            project["value"]
            for project in projects
            if project["name"].lower() == "glance"
        ),
        0,
    )

    manila = next(
        (
            project["value"]
            for project in projects
            if project["name"].lower() == "manila"
        ),
        0,
    )

    # We intentionally focus the card on Glance + Manila.
    core_total = glance + manila

    # Total patch sets returned by Stackalytics.
    all_patch_sets = sum(
        project["value"]
        for project in projects
    )

    # --------------------------------------------------------------
    # Card dimensions
    # --------------------------------------------------------------

    width = 960
    height = 570

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',

        (
            f'<svg '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" '
            f'height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
    ]

    # --------------------------------------------------------------
    # Background
    # --------------------------------------------------------------

    add_rect(
        svg,
        1,
        1,
        width - 2,
        height - 2,
        "#0d1117",
        radius=20,
        stroke="#30363d",
    )

    # OpenStack red accent
    add_rect(
        svg,
        1,
        1,
        8,
        height - 2,
        "#e01b24",
        radius=4,
    )

    # --------------------------------------------------------------
    # Header
    # --------------------------------------------------------------

    add_text(
        svg,
        42,
        43,
        "OPENSTACK CONTRIBUTOR",
        size=13,
        color="#8b949e",
        weight="700",
    )

    add_text(
        svg,
        42,
        79,
        "Sahil Kumbhar",
        size=28,
        color="#f0f6fc",
        weight="700",
    )

    add_text(
        svg,
        42,
        103,
        f"@{USER}",
        size=14,
        color="#8b949e",
    )

    # Upstream badge
    add_rect(
        svg,
        770,
        34,
        140,
        34,
        "#161b22",
        radius=17,
        stroke="#30363d",
    )

    add_text(
        svg,
        840,
        56,
        "UPSTREAM",
        size=12,
        color="#58a6ff",
        weight="700",
        anchor="middle",
    )

    # --------------------------------------------------------------
    # Main statistics
    # --------------------------------------------------------------

    stat_y = 130
    stat_height = 105

    # Total patch sets
    add_rect(
        svg,
        42,
        stat_y,
        270,
        stat_height,
        "#161b22",
        radius=14,
        stroke="#21262d",
    )

    add_text(
        svg,
        64,
        stat_y + 45,
        fmt(all_patch_sets),
        size=38,
        color="#ffffff",
        weight="700",
    )

    add_text(
        svg,
        64,
        stat_y + 75,
        "patch sets",
        size=13,
        color="#8b949e",
        weight="600",
    )

    # Core projects
    add_rect(
        svg,
        330,
        stat_y,
        270,
        stat_height,
        "#161b22",
        radius=14,
        stroke="#21262d",
    )

    add_text(
        svg,
        352,
        stat_y + 45,
        "2",
        size=38,
        color="#ffffff",
        weight="700",
    )

    add_text(
        svg,
        352,
        stat_y + 75,
        "core projects",
        size=13,
        color="#8b949e",
        weight="600",
    )

    # Glance + Manila
    add_rect(
        svg,
        618,
        stat_y,
        292,
        stat_height,
        "#161b22",
        radius=14,
        stroke="#21262d",
    )

    core_percentage = percentage(
        core_total,
        all_patch_sets,
    )

    add_text(
        svg,
        640,
        stat_y + 45,
        f"{core_percentage:.1f}%",
        size=38,
        color="#e01b24",
        weight="700",
    )

    add_text(
        svg,
        640,
        stat_y + 75,
        "Glance + Manila",
        size=13,
        color="#8b949e",
        weight="600",
    )

    # --------------------------------------------------------------
    # Contribution focus
    # --------------------------------------------------------------

    add_text(
        svg,
        42,
        276,
        "CONTRIBUTION FOCUS",
        size=13,
        color="#8b949e",
        weight="700",
    )

    add_text(
        svg,
        42,
        306,
        "Glance → Manila",
        size=21,
        color="#f0f6fc",
        weight="700",
    )

    add_text(
        svg,
        910,
        306,
        f"{fmt(core_total)} patch sets · "
        f"{core_percentage:.1f}% of activity",
        size=14,
        color="#e01b24",
        weight="700",
        anchor="end",
    )

    # Focus bar background
    add_rect(
        svg,
        42,
        321,
        868,
        12,
        "#30363d",
        radius=6,
    )

    # Focus bar
    if core_percentage > 0:
        add_rect(
            svg,
            42,
            321,
            max(
                5,
                868 * core_percentage / 100,
            ),
            12,
            "#e01b24",
            radius=6,
        )

    # --------------------------------------------------------------
    # Project breakdown
    # --------------------------------------------------------------

    add_text(
        svg,
        42,
        372,
        "CORE PROJECT BREAKDOWN",
        size=13,
        color="#8b949e",
        weight="700",
    )

    # Glance
    add_project_row(
        svg,
        "Glance",
        glance,
        core_total if core_total > 0 else 1,
        42,
        404,
        868,
    )

    # Manila
    add_project_row(
        svg,
        "Manila",
        manila,
        core_total if core_total > 0 else 1,
        42,
        450,
        868,
    )

    # --------------------------------------------------------------
    # Footer
    # --------------------------------------------------------------

    svg.append(
        '<line '
        'x1="42" '
        'y1="510" '
        'x2="910" '
        'y2="510" '
        'stroke="#21262d"/>'
    )

    add_text(
        svg,
        42,
        540,
        "Glance → Manila · OpenStack upstream development",
        size=12,
        color="#8b949e",
    )

    # Escape & for valid SVG/XML.
    safe_url = html.escape(
        STACKALYTICS_URL,
        quote=True,
    )

    svg.append(
        f'<a href="{safe_url}" target="_blank">'
        '<text '
        'x="910" '
        'y="540" '
        'text-anchor="end" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="12" '
        'font-weight="600" '
        'fill="#58a6ff">'
        'View Stackalytics →'
        '</text>'
        '</a>'
    )

    svg.append("</svg>")

    return "\n".join(svg)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    print(
        f"Generating OpenStack patch-set card "
        f"for: {USER}"
    )

    projects = get_project_stats()

    if not projects:
        raise RuntimeError(
            "No project statistics returned by Stackalytics."
        )

    print("\nPatch sets by module:")

    for project in projects:
        print(
            f"  {project['name']}: "
            f"{fmt(project['value'])} patch sets"
        )

    # --------------------------------------------------------------
    # Print the two projects we care about
    # --------------------------------------------------------------

    glance = next(
        (
            project["value"]
            for project in projects
            if project["name"].lower() == "glance"
        ),
        0,
    )

    manila = next(
        (
            project["value"]
            for project in projects
            if project["name"].lower() == "manila"
        ),
        0,
    )

    core_total = glance + manila

    print("\nCore projects:")

    print(
        f"  Glance: {fmt(glance)} patch sets"
    )

    print(
        f"  Manila: {fmt(manila)} patch sets"
    )

    print(
        f"  Glance + Manila: "
        f"{fmt(core_total)} patch sets"
    )

    svg = build_svg(projects)

    OUTPUT.write_text(
        svg,
        encoding="utf-8",
    )

    print(
        f"\nCard written to: {OUTPUT}"
    )


if __name__ == "__main__":
    main()
