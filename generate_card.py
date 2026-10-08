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
    f"{BASE}/?user_id={urllib.parse.quote(USER)}"
    "&metric=person-day"
)


def get_json(path, params):
    """Fetch JSON from Stackalytics using curl."""
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"

    print(f"Fetching: {url}")

    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
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


def escape_xml(value):
    """Escape text for safe use inside SVG."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def get_project_stats():
    """Get contribution statistics grouped by OpenStack project."""
    params = {
        "release": "all",
        "metric": "person-day",
        "project_type": "openstack",
        "user_id": USER,
    }

    data = get_json("/api/1.0/stats/modules", params)

    stats = {}

    for item in data.get("stats", []):
        name = item.get("name")
        metric = item.get("metric", 0)

        if name:
            try:
                stats[name] = float(metric)
            except (TypeError, ValueError):
                stats[name] = 0

    return stats


def format_number(value):
    """Format a number nicely."""
    if float(value).is_integer():
        return str(int(value))

    return f"{value:.1f}"


def make_bar(value, maximum, width=250):
    """Create an SVG progress bar."""
    if maximum <= 0:
        percentage = 0
    else:
        percentage = min(value / maximum, 1)

    filled = max(2, int(width * percentage)) if value > 0 else 0

    return f"""
        <rect
            x="0"
            y="0"
            width="{width}"
            height="8"
            rx="4"
            fill="#30363d"
        />
        <rect
            x="0"
            y="0"
            width="{filled}"
            height="8"
            rx="4"
            fill="#58a6ff"
        />
    """


def build_svg(stats):
    """Build the contribution card SVG."""

    # Sort projects by contribution.
    sorted_projects = sorted(
        stats.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    total = sum(stats.values())

    # Projects we want to highlight.
    glance = stats.get("glance", 0)
    manila = stats.get("manila", 0)

    # Keep the remaining projects together.
    other = sum(
        value
        for name, value in stats.items()
        if name not in {"glance", "manila"}
    )

    # The top four projects for the card.
    display_projects = [
        ("Glance", glance),
        ("Manila", manila),
    ]

    if other > 0:
        display_projects.append(("Other OpenStack", other))

    maximum = max(
        [value for _, value in display_projects],
        default=1,
    )

    # Card dimensions.
    width = 900
    height = 430

    project_rows = []

    y = 280

    for project_name, value in display_projects:
        bar = make_bar(value, maximum, 300)

        project_rows.append(
            f"""
            <g transform="translate(55,{y})">
                <text
                    x="0"
                    y="0"
                    fill="#f0f6fc"
                    font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
                    font-size="16"
                    font-weight="600"
                >
                    {escape_xml(project_name)}
                </text>

                <g transform="translate(180,-7)">
                    {bar}
                </g>

                <text
                    x="510"
                    y="0"
                    fill="#8b949e"
                    font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
                    font-size="15"
                >
                    {escape_xml(format_number(value))} person-days
                </text>
            </g>
            """
        )

        y += 42

    svg = f"""<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}"
    role="img"
    aria-label="OpenStack contribution statistics for {escape_xml(USER)}"
>
    <defs>
        <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#0d1117"/>
            <stop offset="100%" stop-color="#161b22"/>
        </linearGradient>

        <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#58a6ff"/>
            <stop offset="100%" stop-color="#79c0ff"/>
        </linearGradient>
    </defs>

    <!-- Background -->
    <rect
        x="0"
        y="0"
        width="{width}"
        height="{height}"
        rx="18"
        fill="url(#background)"
        stroke="#30363d"
        stroke-width="1"
    />

    <!-- OpenStack accent -->
    <rect
        x="0"
        y="0"
        width="7"
        height="{height}"
        rx="3"
        fill="#e44749"
    />

    <!-- Header -->
    <text
        x="55"
        y="55"
        fill="#f0f6fc"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="23"
        font-weight="700"
    >
        OpenStack Contributor
    </text>

    <!-- Upstream badge -->
    <rect
        x="720"
        y="32"
        width="110"
        height="32"
        rx="16"
        fill="#1f6feb"
        fill-opacity="0.18"
        stroke="#1f6feb"
        stroke-opacity="0.45"
    />

    <circle
        cx="738"
        cy="48"
        r="5"
        fill="#3fb950"
    />

    <text
        x="751"
        y="54"
        fill="#58a6ff"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="13"
        font-weight="600"
    >
        Upstream
    </text>

    <!-- User -->
    <text
        x="55"
        y="86"
        fill="#8b949e"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="15"
    >
        Stackalytics · {escape_xml(USER)}
    </text>

    <!-- Main metric -->
    <text
        x="55"
        y="155"
        fill="url(#accent)"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="58"
        font-weight="750"
    >
        {escape_xml(format_number(total))}
    </text>

    <text
        x="55"
        y="182"
        fill="#8b949e"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="16"
    >
        total person-days
    </text>

    <!-- Contribution summary -->
    <text
        x="350"
        y="143"
        fill="#f0f6fc"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="17"
        font-weight="600"
    >
        OpenStack upstream activity
    </text>

    <text
        x="350"
        y="171"
        fill="#8b949e"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="14"
    >
        Glance → Manila
    </text>

    <text
        x="350"
        y="197"
        fill="#8b949e"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="14"
    >
        Image Service → Shared File Systems
    </text>

    <!-- Divider -->
    <line
        x1="55"
        y1="220"
        x2="845"
        y2="220"
        stroke="#30363d"
        stroke-width="1"
    />

    <!-- Project rows -->
    {''.join(project_rows)}

    <!-- Footer -->
    <a
        href="{escape_xml(STACKALYTICS_URL)}"
        target="_blank"
    >
        <text
            x="845"
            y="402"
            text-anchor="end"
            fill="#58a6ff"
            font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
            font-size="14"
            font-weight="600"
        >
            View full Stackalytics stats →
        </text>
    </a>
</svg>
"""

    return svg


def main():
    print(f"Generating OpenStack contribution card for: {USER}")

    stats = get_project_stats()

    if not stats:
        raise RuntimeError(
            "Stackalytics returned no project statistics."
        )

    print("\nContribution statistics:")

    for project, value in sorted(
        stats.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(f"  {project}: {format_number(value)} person-days")

    total = sum(stats.values())

    print(f"\nTotal: {format_number(total)} person-days")

    svg = build_svg(stats)

    OUTPUT.write_text(svg, encoding="utf-8")

    print(f"\nGenerated: {OUTPUT}")


if __name__ == "__main__":
    main()
