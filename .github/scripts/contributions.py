"""Render the last year of GitHub contributions as an animated SVG.

The grid lights up from left to right on each page load and then stays full:
nothing is ever removed. Reads GITHUB_TOKEN and GITHUB_USER, writes the SVG
to the path given as the first argument.
"""

import datetime
import json
import os
import sys
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionLevel } }
      }
    }
  }
}
"""

# Matches the banner: dark card, amber accent.
LEVEL_FILL = {
    "NONE": None,
    "FIRST_QUARTILE": 0.28,
    "SECOND_QUARTILE": 0.5,
    "THIRD_QUARTILE": 0.75,
    "FOURTH_QUARTILE": 1.0,
}
CELL, GAP = 16, 4
STEP = CELL + GAP
LEFT, TOP = 72, 96
WIDTH, HEIGHT = 1200, 284


def fetch_calendar(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def month_labels(weeks):
    labels, previous = [], None
    for x, week in enumerate(weeks):
        month = datetime.date.fromisoformat(week["contributionDays"][0]["date"]).strftime("%b")
        if month != previous and x < len(weeks) - 2:
            labels.append((x, month))
        previous = month
    # A partial first month leaves no room for its label.
    if len(labels) > 1 and labels[1][0] - labels[0][0] < 3:
        labels.pop(0)
    return labels


def render(calendar):
    weeks = calendar["weeks"]
    total = f"{calendar['totalContributions']:,}"
    grid_width = len(weeks) * STEP - GAP

    cells = []
    for x, week in enumerate(weeks):
        for day in week["contributionDays"]:
            cx, cy = LEFT + x * STEP, TOP + day["weekday"] * STEP
            cells.append(f'<rect class="empty" x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" rx="3"/>')
            opacity = LEVEL_FILL[day["contributionLevel"]]
            if opacity:
                delay = x * 28 + day["weekday"] * 10
                cells.append(
                    f'<rect class="lit" x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" rx="3" '
                    f'fill-opacity="{opacity}" style="animation-delay:{delay}ms"/>'
                )

    months = "".join(
        f'<text x="{LEFT + x * STEP}" y="{TOP - 12}" class="mono label">{name}</text>'
        for x, name in month_labels(weeks)
    )
    legend_x = LEFT + grid_width - 5 * STEP - 70
    legend = "".join(
        f'<rect x="{legend_x + 44 + i * STEP}" y="{TOP + 7 * STEP + 12}" width="{CELL}" height="{CELL}" rx="3" '
        + ('class="empty"/>' if o is None else f'fill="#f5a524" fill-opacity="{o}"/>')
        for i, o in enumerate(LEVEL_FILL.values())
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-label="{total} contributions in the last year">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0b1020"/>
      <stop offset="1" stop-color="#131c38"/>
    </linearGradient>
    <style>
      .sans {{ font-family: Inter, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
      .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
      .label {{ fill: #64748b; font-size: 12px; }}
      .empty {{ fill: #1e293b; }}
      .lit {{ fill: #f5a524; opacity: 0; transform-box: fill-box; transform-origin: center;
              animation: light .45s cubic-bezier(.2,.8,.2,1.2) forwards; }}
      @keyframes light {{ from {{ opacity: 0; transform: scale(.3); }} to {{ opacity: 1; transform: scale(1); }} }}
      @media (prefers-reduced-motion: reduce) {{ .lit {{ animation: none; opacity: 1; }} }}
    </style>
  </defs>
  <rect width="{WIDTH}" height="{HEIGHT}" rx="18" fill="url(#bg)"/>
  <text x="{LEFT}" y="58" class="sans" font-size="26" font-weight="700" fill="#f8fafc">{total} contributions in the last year</text>
  {months}
  {"".join(cells)}
  <text x="{legend_x}" y="{TOP + 7 * STEP + 24}" class="mono label">less</text>
  {legend}
  <text x="{legend_x + 44 + 5 * STEP + 4}" y="{TOP + 7 * STEP + 24}" class="mono label">more</text>
</svg>
"""


def main():
    calendar = fetch_calendar(os.environ["GITHUB_USER"], os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(sys.argv[1]) or ".", exist_ok=True)
    with open(sys.argv[1], "w") as f:
        f.write(render(calendar))


if __name__ == "__main__":
    main()
