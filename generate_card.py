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
# Colors
# ============================================================================

BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"

TEXT = "#f0f6fc"
MUTED = "#8b949e"

GREEN = "#3fb950"
BRIGHT_GREEN = "#56d364"
DARK_GREEN = "#238636"

BAR_BG = "#30363d"


# ============================================================================
# Stackalytics API
# ============================================================================

def get_json(path, params):
    """Fetch JSON from Stackalytics."""

    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"

    print(f"Fetching: {url}")

    try:
        result = subprocess.run(
            [
                "curl",

                # Fail on HTTP errors.
                "--fail",

                # Keep stdout clean for JSON parsing.
                "--silent",

                # Still show errors.
                "--show-error",

                # Follow redirects.
                "--location",

                # Stackalytics currently has a certificate-chain
                # problem when accessed from GitHub Actions/Ubuntu.
                "--insecure",

                # Don't spend too long establishing the connection.
                "--connect-timeout",
                "15",

                # Maximum time for one curl invocation.
                "--max-time",
                "120",

                # Retry temporary failures.
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
            "The Stackalytics patches endpoint appears to be "
            "temporarily slow or unavailable."
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
            "Stackalytics returned invalid JSON:\n"
            f"{result.stdout}"
        ) from exc


def get_project_stats():
    """
    Get patch-set statistics from Stackalytics.

    The `patches` metric represents patch sets by module.
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

    if not stats:
        raise RuntimeError(
            "Stackalytics returned no project statistics."
        )

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


# ============================================================================
# Formatting helpers
# ============================================================================

def fmt(value):
    """Format a number cleanly."""

    if value == int(value):
        return str(int(value))

    return f"{value:.1f}"


def percent(value, total):
    """Calculate percentage."""

    if total <= 0:
        return 0

    return (value / total) * 100


def esc(value):
    """Escape XML/SVG content."""

    return html.escape(
        str(value),
        quote=True,
    )


# ============================================================================
# SVG helpers
# ============================================================================

def add_text(
    svg,
    x,
    y,
    content,
    size=16,
    color=TEXT,
    weight="400",
    anchor="start",
):
    """Add an SVG text element."""

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
    """Add an SVG rounded rectangle."""

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


def add_bar(
    svg,
    x,
    y,
    width,
    value,
    max_value,
    color=GREEN,
):
    """Add a horizontal progress bar."""

    # Background.
    add_rect(
        svg,
        x,
        y,
        width,
        10,
        BAR_BG,
        radius=5,
    )

    if max_value <= 0:
        return

    fill_width = width * value / max_value

    if fill_width <= 0:
        return

    add_rect(
        svg,
        x,
        y,
        max(5, fill_width),
        10,
        color,
        radius=5,
    )


# ============================================================================
# Dashboard
# ============================================================================

def build_svg(projects):
    """Build the OpenStack contributor dashboard."""

    # ------------------------------------------------------------------------
    # Find Glance and Manila
    # ------------------------------------------------------------------------

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

    # Total activity returned by Stackalytics.
    total = sum(
        project["value"]
        for project in projects
    )

    # Everything except Glance and Manila.
    supporting = max(
        0,
        total - glance - manila,
    )

    # ------------------------------------------------------------------------
    # Card dimensions
    # ------------------------------------------------------------------------

    width = 960
    height = 590

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

    # Green accent strip.
    add_rect(
        svg,
        1,
        1,
        8,
        height - 2,
        GREEN,
        radius=4,
    )

    # ------------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------------

    add_text(
        svg,
        42,
        44,
        "OPENSTACK CONTRIBUTOR",
        size=13,
        color=MUTED,
        weight="700",
    )

    add_text(
        svg,
        42,
        80,
        "Sahil Kumbhar",
        size=29,
        color=TEXT,
        weight="700",
    )

    add_text(
        svg,
        42,
        105,
        f"@{USER}",
        size=14,
        color=MUTED,
    )

    # Upstream badge.
    add_rect(
        svg,
        770,
        35,
        140,
        35,
        "#122117",
        radius=18,
        stroke="#244b2d",
    )

    add_text(
        svg,
        840,
        58,
        "UPSTREAM",
        size=12,
        color=BRIGHT_GREEN,
        weight="700",
        anchor="middle",
    )

    # ------------------------------------------------------------------------
    # Top statistics
    # ------------------------------------------------------------------------

    stat_y = 132
    stat_height = 105

    # Total patch sets.
    add_rect(
        svg,
        42,
        stat_y,
        270,
        stat_height,
        CARD,
        radius=14,
        stroke="#21262d",
    )

    add_text(
        svg,
        64,
        stat_y + 44,
        fmt(total),
        size=39,
        color=TEXT,
        weight="700",
    )

    add_text(
        svg,
        64,
        stat_y + 75,
        "total patch sets",
        size=13,
        color=MUTED,
        weight="600",
    )

    # Manila.
    add_rect(
        svg,
        330,
        stat_y,
        270,
        stat_height,
        "#102116",
        radius=14,
        stroke="#244b2d",
    )

    add_text(
        svg,
        352,
        stat_y + 44,
        fmt(manila),
        size=39,
        color=BRIGHT_GREEN,
        weight="700",
    )

    add_text(
        svg,
        352,
        stat_y + 75,
        "Manila patch sets",
        size=13,
        color=MUTED,
        weight="600",
    )

    # Primary projects.
    add_rect(
        svg,
        618,
        stat_y,
        292,
        stat_height,
        CARD,
        radius=14,
        stroke="#21262d",
    )

    add_text(
        svg,
        640,
        stat_y + 44,
        "2",
        size=39,
        color=TEXT,
        weight="700",
    )

    add_text(
        svg,
        640,
        stat_y + 75,
        "primary projects",
        size=13,
        color=MUTED,
        weight="600",
    )

    # ------------------------------------------------------------------------
    # Current focus
    # ------------------------------------------------------------------------

    add_text(
        svg,
        42,
        276,
        "CURRENT FOCUS",
        size=13,
        color=MUTED,
        weight="700",
    )

    add_text(
        svg,
        42,
        307,
        "Manila",
        size=24,
        color=BRIGHT_GREEN,
        weight="700",
    )

    add_text(
        svg,
        42,
        331,
        "Shared File Systems Service",
        size=14,
        color=MUTED,
    )

    manila_percentage = percent(
        manila,
        total,
    )

    add_text(
        svg,
        910,
        307,
        f"{fmt(manila)} patch sets · "
        f"{manila_percentage:.1f}% of total",
        size=14,
        color=BRIGHT_GREEN,
        weight="700",
        anchor="end",
    )

    # Manila focus bar.
    add_bar(
        svg,
        42,
        345,
        868,
        manila,
        total,
        color=GREEN,
    )

    # ------------------------------------------------------------------------
    # Contribution breakdown
    # ------------------------------------------------------------------------

    add_text(
        svg,
        42,
        390,
        "CONTRIBUTION BREAKDOWN",
        size=13,
        color=MUTED,
        weight="700",
    )

    # ------------------------------------------------------------------------
    # Glance
    # ------------------------------------------------------------------------

    glance_percentage = percent(
        glance,
        total,
    )

    add_text(
        svg,
        42,
        421,
        "Glance",
        size=15,
        color=TEXT,
        weight="700",
    )

    add_text(
        svg,
        910,
        421,
        f"{fmt(glance)} patch sets · "
        f"{glance_percentage:.1f}%",
        size=14,
        color=MUTED,
        anchor="end",
    )

    add_bar(
        svg,
        42,
        435,
        868,
        glance,
        total,
        color="#2ea043",
    )

    # ------------------------------------------------------------------------
    # Manila
    # ------------------------------------------------------------------------

    add_text(
        svg,
        42,
        475,
        "Manila",
        size=15,
        color=BRIGHT_GREEN,
        weight="700",
    )

    add_text(
        svg,
        910,
        475,
        f"{fmt(manila)} patch sets · "
        f"{manila_percentage:.1f}%",
        size=14,
        color=BRIGHT_GREEN,
        anchor="end",
    )

    add_bar(
        svg,
        42,
        489,
        868,
        manila,
        total,
        color=GREEN,
    )

    # ------------------------------------------------------------------------
    # Supporting repositories
    # ------------------------------------------------------------------------

    supporting_percentage = percent(
        supporting,
        total,
    )

    add_text(
        svg,
        42,
        529,
        "Supporting OpenStack",
        size=14,
        color=MUTED,
        weight="600",
    )

    add_text(
        svg,
        910,
        529,
        f"{fmt(supporting)} patch sets · "
        f"{supporting_percentage:.1f}%",
        size=13,
        color=MUTED,
        anchor="end",
    )

    # ------------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------------

    svg.append(
        '<line '
        'x1="42" '
        'y1="550" '
        'x2="910" '
        'y2="550" '
        'stroke="#21262d"/>'
    )

    add_text(
        svg,
        42,
        573,
        "Glance → Manila · OpenStack upstream development",
        size=12,
        color=MUTED,
    )

    # XML-safe URL.
    safe_url = html.escape(
        STACKALYTICS_URL,
        quote=True,
    )

    svg.append(
        f'<a href="{safe_url}" target="_blank">'
        '<text '
        'x="910" '
        'y="573" '
        'text-anchor="end" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="12" '
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
        f"Generating OpenStack contributor dashboard "
        f"for: {USER}"
    )

    projects = get_project_stats()

    print("\nPatch sets by module:")

    for project in projects:
        print(
            f"  {project['name']}: "
            f"{fmt(project['value'])} patch sets"
        )

    # ------------------------------------------------------------------------
    # Extract Glance / Manila
    # ------------------------------------------------------------------------

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

    total = sum(
        project["value"]
        for project in projects
    )

    supporting = max(
        0,
        total - glance - manila,
    )

    # ------------------------------------------------------------------------
    # Print dashboard statistics
    # ------------------------------------------------------------------------

    print("\nDashboard statistics:")

    print(
        f"  Total patch sets: "
        f"{fmt(total)}"
    )

    print(
        f"  Glance: "
        f"{fmt(glance)}"
    )

    print(
        f"  Manila: "
        f"{fmt(manila)}"
    )

    print(
        f"  Supporting repositories: "
        f"{fmt(supporting)}"
    )

    print(
        f"  Manila share: "
        f"{percent(manila, total):.1f}%"
    )

    # ------------------------------------------------------------------------
    # Generate SVG
    # ------------------------------------------------------------------------

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
