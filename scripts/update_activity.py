"""Generate local profile graphics from GitHub's public contribution calendar.

Run from any directory: python3 scripts/update_activity.py
No credentials, packages or private repository access are needed.
Failed downloads or unexpected HTML leave the last valid graphics intact.
"""
from datetime import date, datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "tricoma035"


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.in_heading = False
        self.heading = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h2" and attrs.get("id") == "js-contribution-activity-description":
            self.in_heading = True
        if attrs.get("data-date") and "data-level" in attrs:
            day = date.fromisoformat(attrs["data-date"])
            level = int(attrs["data-level"])
            if not 0 <= level <= 4:
                raise ValueError("Unexpected contribution level")
            self.days[day] = level

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_heading = False

    def handle_data(self, text):
        if self.in_heading:
            self.heading.append(text)


def render(days, total, dark):
    bg, fg, muted = ("#101b27", "#f0f6fc", "#a7b6c5") if dark else ("#f0f9ff", "#0f172a", "#475569")
    palette = ["#243447", "#164e63", "#0e7490", "#0891b2", "#22d3ee"] if dark else ["#dceaf0", "#a5f3fc", "#67e8f9", "#06b6d4", "#0e7490"]
    start, end = min(days), max(days)
    active = sum(level > 0 for level in days.values())
    updated = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    rects = []
    for day, level in sorted(days.items()):
        offset = (day - start).days
        x, y = 28 + (offset // 7) * 14, 130 + (offset % 7) * 14
        label = escape(f"{day.isoformat()}: intensidad {level}/4")
        rects.append(f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{palette[level]}"><title>{label}</title></rect>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="274" viewBox="0 0 800 274" role="img" aria-labelledby="title desc">
<title id="title">Actividad de {USERNAME} en GitHub</title>
<desc id="desc">{total} contribuciones visibles y {active} días con actividad. Del {start} al {end}.</desc>
<rect width="800" height="274" rx="16" fill="{bg}"/>
<g font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<text x="28" y="36" fill="{fg}" font-size="19" font-weight="600">Actividad en GitHub</text>
<text x="28" y="78" fill="{fg}" font-size="28" font-weight="700">{total:,}</text>
<text x="28" y="101" fill="{muted}" font-size="13">contribuciones visibles</text>
<text x="400" y="78" fill="{fg}" font-size="28" font-weight="700">{active}</text>
<text x="400" y="101" fill="{muted}" font-size="13">días con actividad</text>
{''.join(rects)}
<text x="28" y="252" fill="{muted}" font-size="12">{start.strftime('%d/%m/%Y')} — {end.strftime('%d/%m/%Y')}</text>
<text x="772" y="252" text-anchor="end" fill="{muted}" font-size="12">Actualizado: {updated} UTC</text>
</g></svg>'''


def main():
    request = Request(f"https://github.com/users/{USERNAME}/contributions", headers={"User-Agent": "NusaKa-profile", "Accept-Language": "en-US"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
    calendar = Calendar()
    calendar.feed(html)
    match = re.search(r"([\d,]+)\s+contributions?\b", " ".join(calendar.heading))
    if not match or not 350 <= len(calendar.days) <= 371:
        raise ValueError("Unexpected GitHub calendar; keeping existing graphics")
    total = int(match[1].replace(",", ""))
    start, end = min(calendar.days), max(calendar.days)
    if (end - start).days + 1 != len(calendar.days):
        raise ValueError("Incomplete contribution calendar")
    if abs((date.today() - end).days) > 2:
        raise ValueError("Stale contribution calendar")
    outputs = {name: render(calendar.days, total, dark) for name, dark in [("light", False), ("dark", True)]}
    for theme, svg in outputs.items():
        (ROOT / "assets" / f"activity-{theme}.svg").write_text(svg, encoding="utf-8")
    print(f"Generated {len(calendar.days)} days from GitHub; {total} visible contributions")


if __name__ == "__main__":
    main()
