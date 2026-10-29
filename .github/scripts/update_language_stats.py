#!/usr/bin/env python3
"""Publish aggregate language statistics without publishing private source code."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


OWNER = "PetrShestakov"
PRIVATE_REPO = "PetrShestakov/Chitalka-iOS"
OUTPUT = Path("assets/language-stats.svg")
COLORS = {
    "Swift": "#f05138",
    "Python": "#3572A5",
    "Metal": "#9b8fc7",
    "HTML": "#e34c26",
    "JavaScript": "#f1e05a",
    "Other": "#8b949e",
}


def get_json(url: str, token: str = ""):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PetrShestakov-language-card",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def language_totals(token: str) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    # GitHub's language endpoint returns byte counts, not the underlying code.
    page = 1
    while True:
        repositories = get_json(
            f"https://api.github.com/users/{OWNER}/repos?type=owner&per_page=100&page={page}"
        )
        if not repositories:
            break
        for repo in repositories:
            if repo.get("fork") or repo.get("archived"):
                continue
            languages = get_json(
                f"https://api.github.com/repos/{repo['full_name']}/languages"
            )
            for name, size in languages.items():
                totals[name] += size
        page += 1

    private_languages = get_json(
        f"https://api.github.com/repos/{PRIVATE_REPO}/languages", token
    )
    for name, size in private_languages.items():
        totals[name] += size
    return totals


def svg_chart(languages: dict[str, int]) -> str:
    total = sum(languages.values())
    if total <= 0:
        raise ValueError("No source languages found: refusing to replace chart")

    by_size = sorted(languages.items(), key=lambda entry: entry[1], reverse=True)
    if len(by_size) > 4:
        by_size = by_size[:3] + [("Other", sum(value for _, value in by_size[3:]))]

    x = 28.0
    segments = []
    legend = []
    for idx, (name, size) in enumerate(by_size):
        color = COLORS.get(name, "#8b949e")
        width = 544 * size / total
        segments.append(
            f'<rect x="{x:.2f}" y="95" width="{width:.2f}" height="18" fill="{color}"/>'
        )
        x += width
        column, row = idx % 2, idx // 2
        lx, ly = 28 + column * 275, 157 + row * 35
        label = escape(name)
        legend.append(
            f'<circle cx="{lx + 7}" cy="{ly - 5}" r="6" fill="{color}"/>'
            f'<text x="{lx + 23}" y="{ly}" fill="#c9d1d9" font-size="16" font-weight="500">{label}</text>'
            f'<text x="{lx + 225}" y="{ly}" text-anchor="end" fill="#f0f6fc" font-size="16" font-weight="600">{size / total * 100:.1f}%</text>'
        )

    date_text = datetime.now(timezone.utc).strftime("%d %b %Y")
    desc = escape(
        "; ".join(f"{name} {size / total * 100:.1f} percent" for name, size in by_size)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="250" viewBox="0 0 600 250" role="img" aria-labelledby="title description">
<title id="title">Most Used Languages / Основные языки</title>
<desc id="description">Source code language distribution across public and private repositories: {desc}.</desc>
<rect width="599" height="249" x=".5" y=".5" rx="13" fill="#0d1117" stroke="#30363d"/>
<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif">
<text x="28" y="41" font-size="23" font-weight="700" fill="#f0f6fc">Most Used Languages</text>
<text x="28" y="64" font-size="13" fill="#919da8">Public + private repositories · GitHub language bytes</text>
<rect x="28" y="95" width="544" height="18" rx="9" fill="#30363d"/>
<clipPath id="bar-clip"><rect x="28" y="95" width="544" height="18" rx="9"/></clipPath>
<g clip-path="url(#bar-clip)">{''.join(segments)}</g>
{''.join(legend)}
<text x="28" y="226" font-size="12" fill="#8b949e">Updated: {date_text} · Language totals only; no source code exposed</text>
</g>
</svg>"""


def main() -> None:
    token = os.environ.get("PRIVATE_LANGUAGE_TOKEN", "")
    if not token:
        print("PRIVATE_LANGUAGE_TOKEN is not configured; leaving the current chart unchanged.")
        return
    totals = language_totals(token)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg_chart(totals), encoding="utf-8")
    print("Updated language chart using aggregate counts; private source remains private.")


if __name__ == "__main__":
    main()
