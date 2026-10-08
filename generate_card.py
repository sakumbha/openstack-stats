#!/usr/bin/env python3

import html
import json
import os
import subprocess
import urllib.parse
from pathlib import Path


# ============================================================================
# Configuration
# ============================================================================

BASE = "https://www.stackalytics.io"
OUTPUT = Path("card.svg")

USER = os.environ.get("STACKALYTICS_USER", "sakumbha")

STACKALYTICS_URL = (
    f"{BASE}/?user_id={urllib.parse.quote(USER)}"
    f"&metric=patches"
)


# ============================================================================
# Theme
# ============================================================================

BG = "#0d1117"
CARD = "#161b22"
CARD_ALT = "#0f1419"

BORDER = "#30363d"
BORDER_LIGHT = "#21262d"

TEXT = "#f0f6fc"
MUTED = "#8b949e"

GREEN = "#3fb950"
BRIGHT_GREEN = "#56d364"
DARK_GREEN = "#238636"

GREEN_BG = "#102116"
GREEN_BORDER = "#24552f"


# ============================================================================
# Stackalytics
# ============================================================================

def get_json(path, params):
    """Fetch JSON from Stackalytics."""

    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"

    print(f"Fetching: {url}")

    try:
        result = subprocess.run(
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--location",

                # Stackalytics currently has a certificate-chain
                # issue on Ubuntu/GitHub Actions.
                "--insecure",

                "--connect-timeout",
                "15",

                "--max-time",
                "120",

                "--retry",
                "3",

                "--retry-delay",
                "3",

                "--retry-all-errors",

                "--user-agent",
                "openstack-stats-card/1.0",

                url,
            ],
            capture_output=True,
            text=True,
            timeout=135,
            check=True,
        )

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Stackalytics API timed out after 135 seconds.\n"
            "The Stackalytics patches endpoint may be temporarily slow "
            "or unavailable."
        ) from exc

    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()

        raise RuntimeError(
            "Stackalytics API request failed.\n"
            f"curl exit code: {exc.returncode}\n"
            f"curl error: {stderr}"
        ) from exc

    try:
        return json.loads(result.stdout)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Stackalytics returned invalid JSON."
        ) from exc


def get_project_stats():
    """Return patch-set statistics grouped by OpenStack module."""

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

    if not stats:
        raise RuntimeError(
            "Stackalytics returned no project statistics."
        )

    projects = []

    for item in stats:
        name = item.get("name")
        value = item.get("metric", 0)

        if not name:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        projects.append(
            {
                "name": name,
                "value": value,
            }
        )

    projects.sort(
        key=lambda project: project["value"],
        reverse=True,
    )

    return projects


# ============================================================================
# Helpers
# ============================================================================

def fmt(value):
    """Format numeric values without unnecessary decimals."""

    if value == int(value):
        return str(int(value))

    return f"{value:.1f}"


def esc(value):
    """Escape XML/SVG content."""

    return html.escape(
        str(value),
        quote=True,
    )


def add_text(
    svg,
    x,
    y,
    text,
    size=16,
    color=TEXT,
    weight="400",
    anchor="start",
    letter_spacing=0,
):
    """Add SVG text."""

    spacing = ""

    if letter_spacing:
        spacing = f' letter-spacing="{letter_spacing}px"'

    svg.append(
        f'<text '
        f'x="{x}" '
        f'y="{y}" '
        f'text-anchor="{anchor}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" '
        f'font-weight="{weight}" '
        f'fill="{color}"'
        f'{spacing}>'
        f'{esc(text)}'
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
    """Add SVG rounded rectangle."""

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


def add_line(
    svg,
    x1,
    y1,
    x2,
    y2,
    color=BORDER_LIGHT,
    width=1,
):
    """Add SVG line."""

    svg.append(
        f'<line '
        f'x1="{x1}" '
        f'y1="{y1}" '
        f'x2="{x2}" '
        f'y2="{y2}" '
        f'stroke="{color}" '
        f'stroke-width="{width}"/>'
    )


# ============================================================================
# Project lookup
# ============================================================================

def project_value(projects, name):
    """Find a project by name."""

    for project in projects:
        if project["name"].lower() == name.lower():
            return project["value"]

    return 0


# ============================================================================
# SVG generation
# ============================================================================

def build_svg(projects):
    """Build the OpenStack contributor profile card."""

    glance = project_value(projects, "glance")
    manila = project_value(projects, "manila")

    total = sum(
        project["value"]
        for project in projects
    )

    supporting = max(
        0,
        total - glance - manila,
    )

    # Supporting repositories to show.
    supporting_projects = [
        project["name"]
        for project in projects
        if project["name"].lower()
        not in {"glance", "manila"}
    ]

    # Show at most four names.
    supporting_display = supporting_projects[:4]

    if len(supporting_projects) > 4:
        supporting_display.append("…")

    # ------------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------------

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

    # ------------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------------

    add_rect(
        svg,
        1,
        1,
        width - 2,
        height - 2,
        BG,
        radius=20,
        stroke=BORDER,
    )

    # Green left accent.
    add_rect(
        svg,
        1,
        1,
        7,
        height - 2,
        GREEN,
        radius=4,
    )

    # ------------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------------

    add_text(
        svg,
        40,
        40,
        "OPENSTACK CONTRIBUTOR",
        size=12,
        color=MUTED,
        weight="700",
        letter_spacing=1.2,
    )

    add_text(
        svg,
        40,
        76,
        "Sahil Kumbhar",
        size=28,
        color=TEXT,
        weight="700",
    )

    add_text(
        svg,
        40,
        100,
        f"@{USER}",
        size=14,
        color=MUTED,
    )

    # Upstream badge.
    add_rect(
        svg,
        795,
        28,
        115,
        32,
        GREEN_BG,
        radius=16,
        stroke=GREEN_BORDER,
    )

    add_text(
        svg,
        852,
        49,
        "UPSTREAM",
        size=11,
        color=BRIGHT_GREEN,
        weight="700",
        anchor="middle",
        letter_spacing=0.8,
    )

    # ------------------------------------------------------------------------
    # Top statistics
    # ------------------------------------------------------------------------

    top_y = 125
    box_h = 92

    # Total.
    add_rect(
        svg,
        40,
        top_y,
        275,
        box_h,
        CARD,
        radius=13,
        stroke=BORDER_LIGHT,
    )

    add_text(
        svg,
        62,
        top_y + 39,
        fmt(total),
        size=34,
        color=TEXT,
        weight="700",
    )

    add_text(
        svg,
        62,
        top_y + 68,
        "patch sets",
        size=13,
        color=MUTED,
        weight="600",
    )

    # Manila.
    add_rect(
        svg,
        330,
        top_y,
        275,
        box_h,
        GREEN_BG,
        radius=13,
        stroke=GREEN_BORDER,
    )

    add_text(
        svg,
        352,
        top_y + 39,
        fmt(manila),
        size=34,
        color=BRIGHT_GREEN,
        weight="700",
    )

    add_text(
        svg,
        352,
        top_y + 68,
        "Manila patch sets",
        size=13,
        color=MUTED,
        weight="600",
    )

    # Projects.
    add_rect(
        svg,
        620,
        top_y,
        290,
        box_h,
        CARD,
        radius=13,
        stroke=BORDER_LIGHT,
    )

    add_text(
        svg,
        642,
        top_y + 39,
        "2",
        size=34,
        color=TEXT,
        weight="700",
    )

    add_text(
        svg,
        642,
        top_y + 68,
        "core OpenStack projects",
        size=13,
        color=MUTED,
        weight="600",
    )

    # ------------------------------------------------------------------------
    # Current focus
    # ------------------------------------------------------------------------

    add_text(
        svg,
        40,
        258,
        "CURRENT FOCUS",
        size=12,
        color=MUTED,
        weight="700",
        letter_spacing=1.1,
    )

    # Focus card.
    add_rect(
        svg,
        40,
        278,
        870,
        92,
        CARD,
        radius=14,
        stroke=BORDER,
    )

    # Green indicator.
    add_rect(
        svg,
        40,
        278,
        5,
        92,
        GREEN,
        radius=3,
    )

    # Manila icon / marker.
    add_rect(
        svg,
        64,
        299,
        38,
        38,
        GREEN_BG,
        radius=10,
        stroke=GREEN_BORDER,
    )

    add_text(
        svg,
        83,
        325,
        "M",
        size=18,
        color=BRIGHT_GREEN,
        weight="700",
        anchor="middle",
    )

    add_text(
        svg,
        120,
        313,
        "Manila",
        size=21,
        color=BRIGHT_GREEN,
        weight="700",
    )

    add_text(
        svg,
        120,
        337,
        "Shared File Systems Service",
        size=13,
        color=MUTED,
    )

    add_text(
        svg,
        875,
        317,
        fmt(manila),
        size=27,
        color=TEXT,
        weight="700",
        anchor="end",
    )

    add_text(
        svg,
        875,
        341,
        "patch sets",
        size=12,
        color=MUTED,
        anchor="end",
    )

    # ------------------------------------------------------------------------
    # OpenStack projects
    # ------------------------------------------------------------------------

    add_text(
        svg,
        40,
        404,
        "OPENSTACK PROJECTS",
        size=12,
        color=MUTED,
        weight="700",
        letter_spacing=1.1,
    )

    # Glance card.
    add_rect(
        svg,
        40,
        424,
        425,
        72,
        CARD,
        radius=12,
        stroke=BORDER_LIGHT,
    )

    add_text(
        svg,
        62,
        450,
        "Glance",
        size=16,
        color=TEXT,
        weight="700",
    )

    add_text(
        svg,
        62,
        475,
        "Image Service",
        size=12,
        color=MUTED,
    )

    add_text(
        svg,
        435,
        456,
        fmt(glance),
        size=23,
        color=TEXT,
        weight="700",
        anchor="end",
    )

    add_text(
        svg,
        435,
        477,
        "patch sets",
        size=11,
        color=MUTED,
        anchor="end",
    )

    # Manila card.
    add_rect(
        svg,
        485,
        424,
        425,
        72,
        GREEN_BG,
        radius=12,
        stroke=GREEN_BORDER,
    )

    add_text(
        svg,
        507,
        450,
        "Manila",
        size=16,
        color=BRIGHT_GREEN,
        weight="700",
    )

    add_text(
        svg,
        507,
        475,
        "Shared File Systems Service",
        size=12,
        color=MUTED,
    )

    add_text(
        svg,
        880,
        456,
        fmt(manila),
        size=23,
        color=BRIGHT_GREEN,
        weight="700",
        anchor="end",
    )

    add_text(
        svg,
        880,
        477,
        "patch sets",
        size=11,
        color=MUTED,
        anchor="end",
    )

    # ------------------------------------------------------------------------
    # Supporting repositories
    # ------------------------------------------------------------------------

    add_text(
        svg,
        40,
        524,
        "SUPPORTING OPENSTACK",
        size=11,
        color=MUTED,
        weight="700",
        letter_spacing=1,
    )

    supporting_text = "  ·  ".join(
        supporting_display
    )

    if not supporting_text:
        supporting_text = "Additional OpenStack contributions"

    add_text(
        svg,
        200,
        524,
        supporting_text,
        size=11,
        color=MUTED,
    )

    # ------------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------------

    add_line(
        svg,
        40,
        540,
        910,
        540,
    )

    add_text(
        svg,
        40,
        558,
        "OpenStack upstream development · Glance · Manila",
        size=10,
        color=MUTED,
    )

    safe_url = html.escape(
        STACKALYTICS_URL,
        quote=True,
    )

    svg.append(
        f'<a href="{safe_url}" target="_blank">'
        '<text '
        'x="910" '
        'y="558" '
        'text-anchor="end" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="10" '
        'font-weight="600" '
        f'fill="{BRIGHT_GREEN}">'
        'View Stackalytics →'
        '</text>'
        '</a>'
    )

    svg.append("</svg>")

    return "\n".join(svg)


# ============================================================================
# Main
# ============================================================================

def main():
    print(
        f"Generating OpenStack contributor card for: {USER}"
    )

    projects = get_project_stats()

    print("\nStackalytics project statistics:")

    for project in projects:
        print(
            f"  {project['name']}: "
            f"{fmt(project['value'])} patch sets"
        )

    # ------------------------------------------------------------------------
    # Important values
    # ------------------------------------------------------------------------

    glance = project_value(projects, "glance")
    manila = project_value(projects, "manila")

    total = sum(
        project["value"]
        for project in projects
    )

    supporting = max(
        0,
        total - glance - manila,
    )

    print("\nCard statistics:")
    print(f"  Total patch sets: {fmt(total)}")
    print(f"  Glance: {fmt(glance)}")
    print(f"  Manila: {fmt(manila)}")
    print(f"  Supporting OpenStack: {fmt(supporting)}")

    # ------------------------------------------------------------------------
    # Generate card
    # ------------------------------------------------------------------------

    svg = build_svg(projects)

    OUTPUT.write_text(
        svg,
        encoding="utf-8",
    )

    print(f"\nGenerated: {OUTPUT}")


if __name__ == "__main__":
    main()
