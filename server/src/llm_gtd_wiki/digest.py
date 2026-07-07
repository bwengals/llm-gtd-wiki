"""Daily task digest: read the wiki from S3, build a simple HTML email, send via SES.

Purpose is to keep tasks top-of-mind — NOT a plan for the day. Priorities on top (the word
"priority" highlighted yellow; priority items with an approaching/past-due deadline in bold), then
sections by Area, grouped by Project. Liberal — lists every open task so nothing is forgotten.

Env: WIKI_BUCKET, DIGEST_TO, DIGEST_FROM (verified SES identity), COGNITO_REGION (region).
Deployed as its own Lambda on a daily EventBridge schedule (see infra/digest.tf).
"""
from __future__ import annotations

import datetime
import html
import os
import re

import boto3

HIGHLIGHT = "background-color:#fff3a0"  # soft yellow
BLUE = "background-color:#cfe6ff"       # soft blue
DUE_WINDOW_DAYS = 7


def _s3():
    return boto3.client("s3", region_name=os.environ.get("COGNITO_REGION", "us-west-2"))


def _read(bucket, key) -> str:
    return _s3().get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")


def _list(bucket) -> list[str]:
    keys = []
    for page in _s3().get_paginator("list_objects_v2").paginate(Bucket=bucket):
        keys.extend(o["Key"] for o in page.get("Contents", []))
    return keys


# ---- task text cleanup -------------------------------------------------------
_STRIP = [
    re.compile(r"^\s*- \[ \]\s*"),           # leading checkbox
    re.compile(r"\s*->\s*\[\[[^\]]+\]\]"),   # -> [[link]]
    re.compile(r"\s*#priority\b"),
    re.compile(r"\s*load:\S+"),
    re.compile(r"\s*~\S+"),                   # ~time
]


def _clean(text: str) -> str:
    t = text
    for pat in _STRIP:
        t = pat.sub("", t)
    t = t.replace("**", "").replace("`", "").replace("*", "")  # markdown emphasis
    return t.strip()


def _is_priority(line: str) -> bool:
    return "#priority" in line


# ---- parse -------------------------------------------------------------------
def _area_title(md: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+?)\s*$", md, re.M)
    return m.group(1).split("->")[0].strip() if m else fallback


def parse_area(md: str) -> list[tuple[str, list[str]]]:
    """Return [(group_name, [task_lines]), ...] for an area file."""
    groups: dict[str, list[str]] = {}
    order: list[str] = []
    current = None
    skip = False
    for line in md.splitlines():
        h2 = re.match(r"^##\s+(.+)", line)
        h3 = re.match(r"^###\s+(.+)", line)
        if h2:
            name = h2.group(1).strip()
            skip = name.lower().startswith(("notes", "reference"))
            current = "Single actions" if name.lower().startswith("single") else None
        elif h3:
            name = h3.group(1).strip()
            skip = False
            current = re.sub(r"^Project:\s*", "", name).strip()
        if skip:
            continue
        if re.match(r"^\s*- \[ \]", line):
            g = current or "General"
            if g not in groups:
                groups[g] = []
                order.append(g)
            groups[g].append(line)
    return [(g, groups[g]) for g in order]


def parse_project(md: str) -> tuple[str, str, list[str]]:
    """Return (area, project_name, [task_lines]) for a project file."""
    title = _area_title(md, "Project")
    am = re.search(r"\[\[areas/([a-z0-9_-]+)\]\]", md, re.I)
    area = am.group(1).capitalize() if am else "Other"
    tasks, skip = [], False
    for line in md.splitlines():
        h2 = re.match(r"^##\s+(.+)", line)
        if h2:
            name = h2.group(1).lower()
            skip = name.startswith(("notes", "reference", "ideas", "outreach",
                                    "company tracker", "market context"))
        if not skip and re.match(r"^\s*- \[ \]", line):
            tasks.append(line)
    return area, title, tasks


def parse_radar_due(md: str, today: datetime.date) -> list[str]:
    """Radar items whose deadline is within the window or past due → bold priority lines."""
    out = []
    for line in md.splitlines():
        m = re.search(r"deadline:(\d{4}-\d{2}-\d{2})", line)
        if not m:
            continue
        try:
            due = datetime.date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if (due - today).days <= DUE_WINDOW_DAYS:
            text = re.sub(r"^\s*-\s*", "", line)
            text = re.sub(r"\s*(deadline|surface):\S+", "", text)
            text = re.sub(r"\s*->\s*\[\[[^\]]+\]\]", "", text)
            tag = "past due" if due < today else f"due {due.isoformat()}"
            out.append(f"{text.strip()} ({tag})")
    return out


def parse_accomplishments(md: str, today: datetime.date, days: int = 7) -> list[tuple[datetime.date, str]]:
    """Accomplishments-table rows done within the last `days`, newest first: [(date, task), ...]."""
    out = []
    cutoff = today - datetime.timedelta(days=days)
    for line in md.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) < 2 or cols[0].lower().startswith("date") or set(cols[0]) <= set("-: "):
            continue
        try:
            d = datetime.date.fromisoformat(cols[0])
        except ValueError:
            continue
        if cutoff <= d <= today:
            out.append((d, cols[1]))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


# ---- build + send ------------------------------------------------------------
def build_html(bucket: str, today: datetime.date) -> tuple[str, str]:
    keys = _list(bucket)
    area_sections: dict[str, list[tuple[str, list[str]]]] = {}
    priorities: list[str] = []

    for key in sorted(keys):
        if key.startswith("areas/") and key.endswith(".md"):
            md = _read(bucket, key)
            area = _area_title(md, key)
            groups = parse_area(md)
            if groups:
                area_sections.setdefault(area, [])
                area_sections[area].extend(groups)
            for _, tasks in groups:
                priorities += [_clean(t) for t in tasks if _is_priority(t)]
        elif key.startswith("projects/") and key.endswith(".md"):
            md = _read(bucket, key)
            area, proj, tasks = parse_project(md)
            if tasks:
                area_sections.setdefault(area, [])
                area_sections[area].append((proj, tasks))
            priorities += [_clean(t) for t in tasks if _is_priority(t)]

    due_lines = []
    if "radar.md" in keys:
        due_lines = parse_radar_due(_read(bucket, "radar.md"), today)

    week_acc = []
    if "accomplishments.md" in keys:
        week_acc = parse_accomplishments(_read(bucket, "accomplishments.md"), today, 7)

    def li(text, bold=False):
        t = html.escape(text)
        return f"<li>{'<b>' + t + '</b>' if bold else t}</li>"

    parts = []

    # Priorities on top
    parts.append(
        f'<h3 style="margin-bottom:4px"><span style="{HIGHLIGHT}">Priorities</span></h3>'
    )
    pr = [li(d, bold=True) for d in due_lines] + [li(p) for p in priorities]
    parts.append("<ul>" + ("".join(pr) if pr else "<li>(none)</li>") + "</ul>")

    # By area, grouped by project
    for area in sorted(area_sections):
        parts.append(f'<h3 style="margin-bottom:2px">{html.escape(area)}</h3>')
        for group, tasks in area_sections[area]:
            clean = [_clean(t) for t in tasks]
            clean = [c for c in clean if c]
            if not clean:
                continue
            parts.append(f'<div style="margin-left:8px"><b>{html.escape(group)}</b>')
            parts.append("<ul style='margin-top:2px'>" + "".join(li(c) for c in clean) + "</ul></div>")

    # Accomplished last week — blue, slightly larger header
    if week_acc:
        parts.append(
            f'<h2 style="font-size:19px;margin-bottom:4px"><span style="{BLUE}">Accomplished last week</span></h2>'
        )
        parts.append(
            "<ul>" + "".join(li(f"{d.strftime('%a %b %-d')} — {t}") for d, t in week_acc) + "</ul>"
        )

    subject = f"Tracker daily digest -- {today.strftime('%b %-d, %Y')}"
    body = (
        '<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
        'font-size:15px;line-height:1.35;color:#222">' + "".join(parts) + "</div>"
    )
    return subject, body


def handler(event, context):
    bucket = os.environ["WIKI_BUCKET"]
    to = os.environ["DIGEST_TO"]
    frm = os.environ.get("DIGEST_FROM", to)
    today = datetime.date.today()
    subject, body = build_html(bucket, today)
    ses = boto3.client("ses", region_name=os.environ.get("COGNITO_REGION", "us-west-2"))
    ses.send_email(
        Source=frm,
        Destination={"ToAddresses": [to]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Html": {"Data": body}},
        },
    )
    return {"ok": True, "subject": subject}
