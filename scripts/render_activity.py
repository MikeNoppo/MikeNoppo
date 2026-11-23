import json
import subprocess
import sys
from datetime import date
from itertools import groupby
from pathlib import Path

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def get_calendar(login):
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"login={login}", "-f", f"query={QUERY}"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
        timeout=40,
    )
    return json.loads(result.stdout)["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def summarize(calendar):
    weeks = [week["contributionDays"] for week in calendar["weeks"]]
    days = [day for week in weeks for day in week]
    if not days:
        raise ValueError("GitHub returned an empty contribution calendar")

    weekly_counts = [sum(day["contributionCount"] for day in week) for week in weeks]
    total = sum(weekly_counts)
    if total != calendar["totalContributions"]:
        raise ValueError("The contribution total does not match the daily counts")

    active = [day["contributionCount"] > 0 for day in days]
    streaks = [sum(group) for is_active, group in groupby(active) if is_active]
    return {
        "total": total,
        "weekly_counts": weekly_counts,
        "active_days": sum(active),
        "best_week": max(weekly_counts),
        "longest_streak": max(streaks, default=0),
        "first_day": date.fromisoformat(days[0]["date"]),
        "last_day": date.fromisoformat(days[-1]["date"]),
    }


def chart(activity, left, right, top, bottom):
    counts = activity["weekly_counts"]
    peak = activity["best_week"]
    spacing = (right - left) / len(counts)
    bar_width = spacing * 0.72
    grid = []
    for fraction in (0, 0.5, 1):
        y = bottom - (bottom - top) * fraction
        grid.append(f'<path d="M{left} {y:g}H{right}" stroke="#3e3e3e"/>')
    bars = []
    for index, count in enumerate(counts):
        if not count:
            continue
        height = max(1, (bottom - top) * count / peak)
        x = left + spacing * index + (spacing - bar_width) / 2
        style = ' class="peak" fill="#f2f2f2"' if count == peak else ' fill="#8c8c8c"'
        bars.append(
            f'<rect x="{x:.2f}" y="{bottom - height:.2f}" width="{bar_width:.2f}" height="{height:.2f}"{style}/>'
        )

    start = activity["first_day"].strftime("%b %Y").upper()
    end = activity["last_day"].strftime("%b %Y").upper()
    return "\n".join([
        f'<text class="label" x="{left}" y="{top - 16}">WEEKLY CONTRIBUTIONS</text>',
        *grid,
        *bars,
        f'<text class="label" x="{left}" y="{bottom + 24}">{start}</text>',
        f'<text class="label" x="{right}" y="{bottom + 24}" text-anchor="end">{end}</text>',
    ])


def render(activity, mobile):
    if mobile:
        width, height, margin = 400, 356, 20
        label_y, total_y, unit_y, total_size = 32, 86, 109, 49
        chart_left, chart_top, chart_bottom = 20, 164, 224
        divider, number_y, metric_y = 267, 307, 330
        separator = f"M{margin} 128H{width - margin}"
    else:
        width, height, margin = 896, 288, 32
        label_y, total_y, unit_y, total_size = 47, 114, 145, 60
        chart_left, chart_top, chart_bottom = 326, 63, 145
        divider, number_y, metric_y = 194, 237, 263
        separator = "M298 30V170"

    summary = (
        ("ACTIVE DAYS", f'{activity["active_days"]:,}'),
        ("BEST WEEK", f'{activity["best_week"]:,}'),
        ("LONGEST STREAK", f'{activity["longest_streak"]:,}d'),
    )
    column_width = (width - 2 * margin) / 3
    metrics = []
    for index, (label, value) in enumerate(summary):
        x = margin + index * column_width
        if index:
            metrics.append(f'<path d="M{x - 11:g} {divider + 18}V{height - 18}" stroke="#3e3e3e"/>')
        metrics.extend([
            f'<text class="value" x="{x:g}" y="{number_y}">{value}</text>',
            f'<text class="label" x="{x:g}" y="{metric_y}">{label}</text>',
        ])

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">GitHub activity in the last 12 months</title>
  <desc id="desc">{activity["total"]:,} contributions, {activity["active_days"]:,} active days, {activity["best_week"]:,} contributions in the busiest week, and a longest streak of {activity["longest_streak"]:,} days.</desc>
  <style>
    text {{ font-family: Arial, Helvetica, sans-serif; fill: #f2f2f2; }}
    .label {{ fill: #bcbcbc; font-family: monospace; font-size: {"10" if mobile else "12"}px; letter-spacing: .65px; }}
    .value {{ font-size: {"27" if mobile else "34"}px; font-weight: 700; }}
    @media (prefers-reduced-motion: no-preference) {{
      .peak {{ animation: brighten 900ms ease-out both; }}
    }}
    @keyframes brighten {{ from {{ opacity: .45; }} to {{ opacity: 1; }} }}
  </style>
  <path d="M0 0H{width}V{height}H0Z" fill="#101010"/>
  <path d="M.5 .5H{width - .5}V{height - .5}H.5Z" fill="none" stroke="#595959"/>
  <path d="{separator} M{margin} {divider}H{width - margin}" fill="none" stroke="#3e3e3e"/>
  <text class="label" x="{margin}" y="{label_y}">LAST 12 MONTHS</text>
  <text x="{margin - 2}" y="{total_y}" font-size="{total_size}" font-weight="700" letter-spacing="-1.5">{activity["total"]:,}</text>
  <text x="{margin}" y="{unit_y}" font-size="{"16" if mobile else "20"}">Total contributions</text>
  {chart(activity, chart_left, width - margin, chart_top, chart_bottom)}
  {chr(10).join(metrics)}
</svg>
"""


def main(login):
    activity = summarize(get_calendar(login))
    assets = Path(__file__).resolve().parents[1] / "assets"
    for name, mobile in [("github-activity.svg", False), ("github-activity-mobile.svg", True)]:
        (assets / name).write_text(render(activity, mobile), encoding="utf-8")
    print(f'Rendered {activity["total"]:,} contributions across {len(activity["weekly_counts"])} weeks')


if __name__ == "__main__":
    main(sys.argv[1])
