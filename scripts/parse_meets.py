#!/usr/bin/env python3
"""Parse Meet Maestro PDF result reports into structured JSON."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "pdfs"
DATA_DIR = ROOT / "data"
MEETS_DIR = DATA_DIR / "meets"

TEAM_CODES = {
    "EGU": "Excel Grown-Ups",
    "NAC": "NAC Grown-Ups",
    "7H": "7 Hills GrownUps",
    "CWOOD": "Cottonwood",
    "WHIT": "Whitworth",
    "RICH": "Richland Gators",
    "NRR": "Nash River Rats",
    "NASH": "Nash Dolphins",
    "ENS": "Ensworth Aquatic",
    "BSTC": "BSTC",
    "UNA": "Unattached",
    "SSS": "Sour Scandinavia",
    "WB": "Wave Brakers",
    "FA": "Nash Free Agents",
    "JCC": "JCC Grown-Ups",
    "LIFE": "Lifetime Masters",
}

# Reverse lookup for common full names → codes
TEAM_NAME_TO_CODE = {v.lower(): k for k, v in TEAM_CODES.items()}
TEAM_NAME_TO_CODE.update(
    {
        "excel grown-ups": "EGU",
        "nac grown-ups": "NAC",
        "7 hills grownups": "7H",
        "cottonwood": "CWOOD",
        "whitworth": "WHIT",
        "richland gators": "RICH",
        "nash river rats": "NRR",
        "nash dolphins": "NASH",
        "ensworth aquatic": "ENS",
        "nash free agents": "FA",
        "sour scandinavia": "SSS",
        "wave brakers": "WB",
        "jcc grown-ups": "JCC",
        "lifetime masters": "LIFE",
    }
)

POINT_VALUES = [
    40,
    34,
    32,
    30,
    28,
    26,
    24,
    22,
    20,
    18,
    17,
    16,
    15,
    14,
    13,
    12,
    11,
    9,
    7,
    6,
    5,
    4,
    3,
    2,
    1,
]

STATUS_TOKENS = {"NS", "DQ", "DFS", "SCR", "DNF"}

# Meet Maestro exports spell some swimmers inconsistently across PDFs, which
# otherwise splits one person into two athlete records. Pairs are auto-detected
# (see merge_duplicate_athletes) and can be forced or blocked here.
FORCE_MERGE: list[tuple[str, str]] = []
BLOCK_MERGE: set[tuple[str, str]] = {
    # Different ages (28 vs 34) and very different times — treat as two people.
    ("tomsic|zach", "tomsick|zachary"),
}

MEET_FILES = [
    {
        "id": "meet-1-d1",
        "pdf": "meet1-d1-cottonwood.pdf",
        "short_name": "Meet 1 D1",
        "division": "D1",
    },
    {
        "id": "meet-1-d2",
        "pdf": "meet1-d2-jcc.pdf",
        "short_name": "Meet 1 D2",
        "division": "D2",
    },
    {
        "id": "meet-2-d1",
        "pdf": "meet2-d1-7hills.pdf",
        "short_name": "Meet 2 D1",
        "division": "D1",
    },
    {
        "id": "meet-2-d2",
        "pdf": "meet2-d2-westhaven.pdf",
        "short_name": "Meet 2 D2",
        "division": "D2",
    },
    {
        "id": "meet-3-d1",
        "pdf": "meet3-d1-richland.pdf",
        "short_name": "Meet 3 D1",
        "division": "D1",
    },
    {
        "id": "meet-3-d2",
        "pdf": "meet3-d2-bstc.pdf",
        "short_name": "Meet 3 D2",
        "division": "D2",
    },
    {
        "id": "championship",
        "pdf": "championship-williamson.pdf",
        "short_name": "Championship",
        "division": "Combined",
    },
]

FOOTER_RE = re.compile(
    r"SwimTopia Meet Maestro[^\n]*\n"
    r"(?:\d{1,2}/\d{1,2}/\d{2},?\s+\d{1,2}:\d{2}\s+[AP]M[^\n]*\n)?"
    r"(?:https://maestro\.swimtopia\.com/[^\n]+\n)?"
    r"(?:Results .+? Page \d+ of \d+\n)?",
)

EVENT_HEADER_RE = re.compile(
    r"^#(?P<code>\d+[A-Z]?)\s*"
    r"(?P<body>"
    r"Mixed\s+Open\s+\d+yd\s+.+"
    r"|Women\s+\d+(?:-\d+| & Over)\s+\d+yd\s+.+"
    r"|Men\s+\d+(?:-\d+| & Over)\s+\d+yd\s+.+"
    r")$",
    re.M,
)

# Compact headers like #4CMen 40-4925yd Freestyle
EVENT_HEADER_COMPACT_RE = re.compile(
    r"^#(?P<code>\d+[A-Z]?)"
    r"(?P<body>"
    r"Mixed\s*Open\s*\d+yd\s*.+"
    r"|Women\s*\d+(?:-\d+| & Over)\s*\d+yd\s*.+"
    r"|Men\s*\d+(?:-\d+| & Over)\s*\d+yd\s*.+"
    r")$",
    re.M,
)

DIVISION_RE = re.compile(r"^(?:D\d+)?(?P<age>\d{2})(?:-\d{2}| & Over)?$", re.M)


@dataclass
class MeetMeta:
    id: str
    short_name: str
    pdf: str
    division: str
    name: str
    venue: str
    date: str
    date_display: str


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def clean_text(text: str) -> str:
    # Normalize whitespace oddities but keep newlines
    text = text.replace("\u00a0", " ")
    text = FOOTER_RE.sub("\n", text)
    # Drop column header lines
    text = re.sub(
        r"^Pl (?:Athlete|Name|Relay Team|Team).*$",
        "",
        text,
        flags=re.M,
    )
    text = re.sub(r"^No Division\s*$", "", text, flags=re.M)
    # Collapse 3+ blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def parse_meet_header(text: str, meta: dict) -> MeetMeta:
    m = re.search(
        r"Results\s+(?P<name>.+?)\s+—\s+(?P<date>[A-Za-z]+\s+\d{1,2},\s+\d{4})",
        text,
    )
    if not m:
        raise ValueError(f"Could not parse meet header for {meta['pdf']}")
    name = m.group("name").strip()
    date_display = m.group("date").strip()
    date = datetime.strptime(date_display, "%b %d, %Y").date().isoformat()
    venue_m = re.search(r"@\s*(.+)$", name)
    venue = venue_m.group(1).strip() if venue_m else ""
    return MeetMeta(
        id=meta["id"],
        short_name=meta["short_name"],
        pdf=meta["pdf"],
        division=meta["division"],
        name=name,
        venue=venue,
        date=date,
        date_display=date_display,
    )


def looks_like_time(token: str) -> bool:
    token = token.strip()
    if not token or token in STATUS_TOKENS | {"NT"}:
        return False
    return bool(re.fullmatch(r"\d+:\d{2}\.\d{2}", token) or re.fullmatch(r"\d+\.\d{2}", token))


def time_to_seconds(token: str | None) -> float | None:
    if not token or not looks_like_time(token):
        return None
    if ":" in token:
        mins, secs = token.split(":")
        return int(mins) * 60 + float(secs)
    return float(token)


def split_time_and_points(raw: str) -> tuple[str | None, int | None, str]:
    """Return (time, points, status). status is 'official'/'NS'/etc."""
    raw = raw.strip()
    if not raw:
        return None, None, "unknown"
    if raw in STATUS_TOKENS:
        return None, None, raw
    # Space-separated time + optional points
    parts = raw.split()
    if len(parts) == 2 and looks_like_time(parts[0]) and parts[1].isdigit():
        return parts[0], int(parts[1]), "official"
    if len(parts) == 1 and looks_like_time(parts[0]):
        return parts[0], None, "official"

    # Glued time+points: try known point suffixes (longest first already)
    for pts in POINT_VALUES:
        suffix = str(pts)
        if raw.endswith(suffix):
            time_part = raw[: -len(suffix)]
            if looks_like_time(time_part):
                return time_part, pts, "official"
    if looks_like_time(raw):
        return raw, None, "official"
    return None, None, "unknown"


def split_seed_official_points(raw: str) -> tuple[str | None, str | None, int | None, str]:
    """Parse championship-style seed/official/points blob."""
    raw = raw.strip()
    if not raw:
        return None, None, None, "unknown"
    if raw in STATUS_TOKENS:
        return None, None, None, raw
    if raw.endswith(" NS") or raw.endswith("NS"):
        seed = raw[:-2].strip() if raw.endswith("NS") else raw[:-3].strip()
        seed = None if seed in ("", "NT") else seed
        if seed and not looks_like_time(seed):
            # maybe glued NT
            seed = None if seed == "NT" else seed
        return seed if (seed and looks_like_time(seed)) else None, None, None, "NS"

    tokens = raw.split()
    if len(tokens) >= 2:
        # e.g. "11.52 11.39 20" or "11.52 11.3920" or "NT 25.13 12"
        seed_tok = tokens[0]
        rest = " ".join(tokens[1:])
        seed = None if seed_tok == "NT" else (seed_tok if looks_like_time(seed_tok) else None)
        time, pts, status = split_time_and_points(rest)
        return seed, time, pts, status

    # Fully glued cases like 11.5211.3920 or 1:05.871:03.5617 or NT25.1312
    if raw.startswith("NT"):
        time, pts, status = split_time_and_points(raw[2:])
        return None, time, pts, status

    # Two times glued, optional points: find first valid time prefix then rest
    for i in range(4, len(raw) - 3):
        left = raw[:i]
        right = raw[i:]
        if looks_like_time(left):
            time, pts, status = split_time_and_points(right)
            if status == "official" and time:
                return left, time, pts, status
    time, pts, status = split_time_and_points(raw)
    return None, time, pts, status


def normalize_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    return name


def split_name(name: str) -> tuple[str, str]:
    if "," in name:
        last, first = name.split(",", 1)
        return first.strip(), last.strip()
    parts = name.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return name, ""


def athlete_key(name: str) -> str:
    first, last = split_name(name)
    return f"{last.lower()}|{first.lower()}"


def team_code_for(team: str) -> str | None:
    return TEAM_NAME_TO_CODE.get(team.lower().strip())


def expand_team_code(code: str) -> str:
    return TEAM_CODES.get(code, code)


def parse_event_body(code: str, body: str) -> dict:
    body = re.sub(r"\s+", " ", body).strip()
    # Insert spaces in compact forms: Men40-4925yd Freestyle / Mixed Open50yd PRO 50 Free
    body = re.sub(r"(Mixed|Women|Men)\s*", r"\1 ", body)
    body = re.sub(r"(Open)\s*", r"\1 ", body)
    body = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1-\2", body)
    body = re.sub(r"(& Over)\s*", r"\1 ", body)
    body = re.sub(r"(\d+)(yd)", r"\1\2 ", body)
    body = re.sub(r"\s+", " ", body).strip()

    is_relay = "Relay" in body
    is_open = "Open" in body

    gender = "Mixed"
    if body.startswith("Women"):
        gender = "Women"
    elif body.startswith("Men"):
        gender = "Men"

    age_group = "Open"
    ag = re.search(r"(\d{2}-\d{2}|\d{2} & Over)", body)
    if ag:
        age_group = ag.group(1)

    dist_m = re.search(r"(\d+yd)", body)
    distance = dist_m.group(1) if dist_m else None

    stroke = None
    for candidate in [
        "Medley Relay",
        "Freestyle Relay",
        "PRO 50 Free",
        "Freestyle",
        "Butterfly",
        "Backstroke",
        "Breaststroke",
        "IM",
    ]:
        if candidate in body:
            stroke = candidate
            break

    # Friendly event label without age/gender prefix for grouping
    stroke_key = stroke or body
    if stroke == "PRO 50 Free":
        event_key = "Open 50 Free"
    elif is_relay:
        event_key = f"{distance} {stroke}" if distance else stroke
    else:
        event_key = f"{distance} {stroke}" if distance and stroke else body

    display = body
    # Normalize display spacing
    display = re.sub(r"\s+", " ", display)

    return {
        "code": code,
        "number": int(re.match(r"\d+", code).group()),
        "name": display,
        "gender": gender,
        "age_group": age_group,
        "distance": distance,
        "stroke": stroke,
        "event_key": event_key,
        "is_relay": is_relay,
        "is_open": is_open,
    }


def normalize_event_body(body: str) -> str:
    """Insert spaces into compact Meet Maestro event titles."""
    body = re.sub(r"(Women|Men|Mixed)", r"\1 ", body)
    body = re.sub(r"(Open)", r"\1 ", body)
    # 40-4925yd / 80 & Over25yd — but never split 100yd into 10 + 0yd
    body = re.sub(
        r"(?P<ag>\d{2}-\d{2}|\d{2} & Over)(?P<dist>\d+yd)",
        r"\g<ag> \g<dist>",
        body,
    )
    body = re.sub(r"\s+", " ", body).strip()
    return body


def find_events(text: str) -> list[tuple[int, dict]]:
    events = []
    for rx in (EVENT_HEADER_RE, EVENT_HEADER_COMPACT_RE):
        for m in rx.finditer(text):
            code = m.group("code")
            body_norm = normalize_event_body(m.group("body"))
            info = parse_event_body(code, body_norm)
            events.append((m.start(), info, m.end()))
    # Deduplicate by start position (prefer longer/cleaner)
    by_start = {}
    for start, info, end in events:
        by_start[start] = (start, info, end)
    ordered = [by_start[k] for k in sorted(by_start)]
    return ordered


def fix_glued_seven_hills(place_raw: str, team: str, team_code: str | None = None) -> tuple[str, str]:
    """PDF text often glues place into '7 Hills' (e.g. '27 Hills' == place 2)."""
    team = team.strip()
    code = (team_code or "").upper()
    if code == "7H" or re.match(r"Hills\b", team) or team.lower().startswith("hills"):
        if place_raw not in {"--", ""} and place_raw.endswith("7"):
            place_raw = place_raw[:-1] or "--"
        if not re.match(r"7\s*Hills", team, re.I):
            team = "7 Hills GrownUps"
    return place_raw, team


def repair_glued_legs(line: str) -> str:
    """Restore the paren Meet Maestro drops between a swimmer's age and the next leg.

    Two variants show up, both of which silently delete the following swimmer:

      "3)Branscombe, Lauren (304)Gibbons, Julie (30)"
        -> age 30, then leg 4  (closing paren lost)
      "1)Guillamondegui, Oscar (2)Adcock, Steph (60)"
        -> age unknown, then leg 2  (age digits lost entirely)

    Adult ages are always two digits, so any one- or three-digit parenthesised
    group is a collision with the next leg number.
    """
    line = re.sub(r"\((\d{2})([1-9])\)", r"(\1) \2)", line)
    return re.sub(r"\((\d)\)", r"() \1)", line)


def parse_swimmers_line(line: str) -> list[dict]:
    swimmers = []
    # The name may itself contain a parenthetical nickname ("Owens, Eric (Dustin)").
    # That inner group must contain a letter, otherwise "(4 3)Hastings" would read
    # as a nickname and swallow the next leg marker.
    for m in re.finditer(
        r"(\d+)\)\s*((?:[^()]|\([^()]*[A-Za-z][^()]*\))+?)\s*\((\d+|—|-)?\)",
        repair_glued_legs(line),
    ):
        leg = int(m.group(1))
        name = normalize_name(m.group(2))
        age_raw = m.group(3)
        age = int(age_raw) if age_raw and age_raw.isdigit() else None
        if name in {"—", "-", ""}:
            continue
        first, last = split_name(name)
        swimmers.append(
            {
                "leg": leg,
                "name": name,
                "first_name": first,
                "last_name": last,
                "age": age,
            }
        )
    return swimmers


def parse_multiline_individual(block: str) -> list[dict]:
    results = []
    # Result records can span page breaks; stitch Age/time onto place lines.
    pattern = re.compile(
        r"^(?P<place>--|\d+)\*?\s*(?P<name>[A-Z][^:\n]*?)\s*\n+"
        r"Age\s*(?P<age>\d+)\s*·\s*(?P<team>[^\n]+?)\s*\n+"
        r"(?P<raw>(?:NS|DQ|DFS|SCR|DNF|[\d:.]+(?:\s+\d+)?))\s*$",
        re.M,
    )
    for m in pattern.finditer(block):
        place_raw = m.group("place")
        name = normalize_name(m.group("name"))
        # Guard against event-like false positives
        if name.startswith("#") or name.startswith("Pl "):
            continue
        age = int(m.group("age"))
        team = normalize_name(m.group("team"))
        time, pts, status = split_time_and_points(m.group("raw"))
        first, last = split_name(name)
        results.append(
            {
                "place": None if place_raw == "--" else int(place_raw),
                "name": name,
                "first_name": first,
                "last_name": last,
                "age": age,
                "team": team,
                "team_code": team_code_for(team),
                "seed": None,
                "time": time,
                "time_seconds": time_to_seconds(time),
                "points": pts,
                "status": status,
            }
        )
    return results


def parse_championship_individual(block: str) -> list[dict]:
    results = []
    # 1 Voelker, Brian 41EGU 11.52 11.3920
    # --Buehler, Stephen 49EGU 12.64 NS
    # 6Gilley, Phil 43NAC NT 15.3313
    pattern = re.compile(
        r"^(?P<place>--|\d+)\*?\s*(?P<name>[A-Z][A-Za-z .'-]+?,\s*[A-Za-z .'-]+?)\s+"
        r"(?P<age>\d{1,3})(?P<code>[A-Z0-9]{2,5})\s+"
        r"(?P<rest>.+?)\s*$",
        re.M,
    )
    for m in pattern.finditer(block):
        place_raw = m.group("place")
        name = normalize_name(m.group("name"))
        age = int(m.group("age"))
        code = m.group("code")
        seed, time, pts, status = split_seed_official_points(m.group("rest").strip())
        first, last = split_name(name)
        results.append(
            {
                "place": None if place_raw == "--" else int(place_raw),
                "name": name,
                "first_name": first,
                "last_name": last,
                "age": age,
                "team": expand_team_code(code),
                "team_code": code if code in TEAM_CODES else code,
                "seed": seed,
                "time": time,
                "time_seconds": time_to_seconds(time),
                "points": pts,
                "status": status,
            }
        )
    return results


def _relay_divisions(block: str) -> list[tuple[int, str]]:
    divisions = []
    # Handles 18-29, D1818-29, 1818-29, 80 & Over, etc.
    for m in re.finditer(
        r"^(?:D)?(?:\d{2})?(?P<label>\d{2}-\d{2}|\d{2} & Over)\s*$",
        block,
        re.M,
    ):
        divisions.append((m.start(), m.group("label")))
    return divisions


def _division_at(divisions: list[tuple[int, str]], pos: int) -> str | None:
    division = None
    for dpos, label in divisions:
        if dpos < pos:
            division = label
        else:
            break
    return division


def parse_multiline_relay(block: str) -> list[dict]:
    results = []
    divisions = _relay_divisions(block)
    pattern = re.compile(
        r"^(?P<place>--|\d+)\*?\s*(?P<team>(?:7\s+)?[A-Z][^\n]*?)\s*\n"
        r"Relay\s+(?P<relay>[A-Z])\s*·\s*(?P<code>[A-Z0-9]+)\s*\n"
        r"(?P<raw>NS|DQ|DFS|[\d:.]+(?:\s+\d+)?)\s*\n"
        r"(?P<legs>1\).+(?:\n\d+\).+)?)",
        re.M,
    )

    for m in pattern.finditer(block):
        place_raw, team = fix_glued_seven_hills(
            m.group("place"), normalize_name(m.group("team")), m.group("code")
        )
        time, pts, status = split_time_and_points(m.group("raw"))
        legs_text = m.group("legs").replace("\n", " ")
        swimmers = parse_swimmers_line(legs_text)
        results.append(
            {
                "place": None if place_raw == "--" else int(place_raw),
                "team": team,
                "team_code": m.group("code"),
                "relay": m.group("relay"),
                "division": _division_at(divisions, m.start()),
                "seed": None,
                "time": time,
                "time_seconds": time_to_seconds(time),
                "points": pts,
                "status": status,
                "swimmers": swimmers,
            }
        )
    return results


def parse_championship_relay(block: str) -> list[dict]:
    results = []
    divisions = _relay_divisions(block)

    # 2 Excel Grown-Ups BEGU 57.6455.4834
    # 1 Nash River Rats ANRR 54.45 51.0740
    pattern = re.compile(
        r"^(?P<place>--|\d+)\*?\s*(?P<team>(?:7\s+)?[A-Z][A-Za-z0-9 .'-]+?)\s+"
        r"(?P<relay>[A-Z])(?P<code>[A-Z0-9]{2,5})\s+"
        r"(?P<rest>\S+(?:\s+\S+)?)\s*\n"
        r"(?P<legs>1\).+(?:\n\d+\).+)?)",
        re.M,
    )
    for m in pattern.finditer(block):
        code = m.group("code")
        place_raw, team = fix_glued_seven_hills(
            m.group("place"), normalize_name(m.group("team")), code
        )
        seed, time, pts, status = split_seed_official_points(m.group("rest").strip())
        legs_text = m.group("legs").replace("\n", " ")
        swimmers = parse_swimmers_line(legs_text)
        results.append(
            {
                "place": None if place_raw == "--" else int(place_raw),
                "team": team if team else expand_team_code(code),
                "team_code": code,
                "relay": m.group("relay"),
                "division": _division_at(divisions, m.start()),
                "seed": seed,
                "time": time,
                "time_seconds": time_to_seconds(time),
                "points": pts,
                "status": status,
                "swimmers": swimmers,
            }
        )
    return results


def parse_event_results(event: dict, block: str, is_championship: bool) -> list[dict]:
    if event["is_relay"]:
        if is_championship:
            results = parse_championship_relay(block)
            if not results:
                results = parse_multiline_relay(block)
        else:
            results = parse_multiline_relay(block)
            if not results:
                results = parse_championship_relay(block)
        return results

    if is_championship:
        results = parse_championship_individual(block)
        # Some championship pages may still use multiline for a few events; unlikely
        if not results:
            results = parse_multiline_individual(block)
        return results

    results = parse_multiline_individual(block)
    if not results:
        results = parse_championship_individual(block)
    return results


# Fastest a human has ever gone in short-course yards, with slack. A handful of
# results in the source PDFs come in under these — always a lone outlier against
# the swimmer's own times, so the clock almost certainly caught a split rather
# than the finish. Meet Maestro still scored and placed those swims, so we keep
# the result and flag the time instead of discarding either.
IMPOSSIBLE_UNDER = {
    "25yd Freestyle": 8.5,
    "25yd Backstroke": 9.5,
    "25yd Breaststroke": 10.5,
    "25yd Butterfly": 9.0,
    "50yd IM": 21.0,
    "100yd IM": 45.0,
    "Open 50 Free": 18.0,
}


def flag_suspect_times(events: list[dict]) -> None:
    for event in events:
        floor = IMPOSSIBLE_UNDER.get(event["event_key"])
        for r in event["results"]:
            seconds = r.get("time_seconds")
            r["suspect_time"] = bool(floor and seconds is not None and seconds < floor)


# A swim this much faster than the swimmer's own best in the same event. Nobody
# beats their season best by a third, so a ratio this extreme means the clock
# measured a shorter distance than it should have. Compared against their best
# rather than their average, because slow swimmers post wildly uneven times and
# an average would flag their good days.
OUTLIER_RATIO = 0.7


def flag_outlier_times(meets: list[dict]) -> None:
    """Catch split-length times that clear the absolute floor.

    A 56-year-old's 100 IM of 50.09 is not impossible on its own, but it is
    when her other three swims of the season are 1:35, 1:38 and 1:48. Needs the
    canonical athlete_key from link_meets_to_athletes, so it runs across meets
    rather than inside parse_meet.
    """
    swims: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for meet in meets:
        for event in meet["events"]:
            if event["is_relay"]:
                continue
            for r in event["results"]:
                if r.get("status") != "official" or r.get("time_seconds") is None:
                    continue
                if not r.get("athlete_key"):
                    continue
                swims[(r["athlete_key"], event["event_key"])].append(r)

    for results in swims.values():
        if len(results) < 3:
            continue
        for r in results:
            best_of_rest = min(x["time_seconds"] for x in results if x is not r)
            if r["time_seconds"] < best_of_rest * OUTLIER_RATIO:
                r["suspect_time"] = True


def add_field_sizes(events: list[dict]) -> None:
    for event in events:
        results = event["results"]
        if event["is_relay"]:
            timed = [r for r in results if r.get("status") == "official" and r.get("time")]
            field = len(timed)
            for r in results:
                r["field_size"] = field if r.get("status") == "official" else len(results)
            continue

        timed = [r for r in results if r.get("status") == "official" and r.get("time_seconds") is not None]
        field = len(timed)
        for r in results:
            r["age_group_field"] = field


def add_overall_rankings(events: list[dict]) -> None:
    """Compute All Men / All Women ranks across age groups for the same stroke.

    Unlike age-group place, this ranking is ours rather than the meet's, so
    suspect times sit it out instead of leapfrogging the whole field.
    """
    groups: dict[tuple, list[tuple[dict, dict]]] = defaultdict(list)
    for event in events:
        if event["is_relay"] or event["is_open"]:
            # Open events: overall == official place
            timed = [
                r
                for r in event["results"]
                if r.get("status") == "official"
                and r.get("time_seconds") is not None
                and not r.get("suspect_time")
            ]
            timed_sorted = sorted(timed, key=lambda r: r["time_seconds"])
            total = len(timed_sorted)
            rank_map = {id(r): i + 1 for i, r in enumerate(timed_sorted)}
            for r in event["results"]:
                if id(r) in rank_map:
                    r["overall_place"] = rank_map[id(r)]
                    r["overall_field"] = total
                    r["overall_label"] = "Overall"
                else:
                    r["overall_place"] = None
                    r["overall_field"] = total
                    r["overall_label"] = "Overall"
            continue

        key = (event["gender"], event["distance"], event["stroke"])
        for r in event["results"]:
            if (
                r.get("status") == "official"
                and r.get("time_seconds") is not None
                and not r.get("suspect_time")
            ):
                groups[key].append((event, r))

    for key, items in groups.items():
        items_sorted = sorted(items, key=lambda er: er[1]["time_seconds"])
        total = len(items_sorted)
        gender = key[0]
        label = f"All {gender}" if gender in {"Men", "Women"} else "Overall"
        rank_map = {id(r): i + 1 for i, (_, r) in enumerate(items_sorted)}
        # Also mark non-timed in those events
        seen_events = {id(e) for e, _ in items}
        for event in events:
            if id(event) not in seen_events:
                continue
            if (event["gender"], event["distance"], event["stroke"]) != key:
                continue
            for r in event["results"]:
                r["overall_place"] = rank_map.get(id(r))
                r["overall_field"] = total
                r["overall_label"] = label


def parse_meet(meta: dict) -> dict:
    pdf_path = PDF_DIR / meta["pdf"]
    raw = extract_text(pdf_path)
    meet = parse_meet_header(raw, meta)
    text = clean_text(raw)
    is_championship = meet.division == "Combined" or meet.id == "championship"

    event_spans = find_events(text)
    events = []
    for idx, (start, info, end) in enumerate(event_spans):
        block_end = event_spans[idx + 1][0] if idx + 1 < len(event_spans) else len(text)
        block = text[end:block_end]
        # Championship PDFs append team score tables after the last event
        scores_at = re.search(
            r"\n(?:Women|Men|Combined) Team Scores\b|\nCombined Team Scores\b",
            block,
        )
        if scores_at:
            block = block[: scores_at.start()]
        results = parse_event_results(info, block, is_championship)
        event = {**info, "results": results}
        events.append(event)

    flag_suspect_times(events)
    add_field_sizes(events)
    add_overall_rankings(events)

    return {
        "id": meet.id,
        "short_name": meet.short_name,
        "division": meet.division,
        "name": meet.name,
        "venue": meet.venue,
        "date": meet.date,
        "date_display": meet.date_display,
        "source_pdf": f"pdfs/{meet.pdf}",
        "event_count": len(events),
        "result_count": sum(len(e["results"]) for e in events),
        "events": events,
    }


def meet_team_scores(meet: dict) -> list[dict]:
    """Team scores for a single meet.

    Lives in the meets index so the home page can show who actually won the
    Championship without downloading that meet's full result file.
    """
    rows: dict[str, dict] = {}
    swimmers: dict[str, set[str]] = defaultdict(set)

    for event in meet["events"]:
        for r in event["results"]:
            team = r.get("team")
            if not team:
                continue
            row = rows.setdefault(
                team,
                {
                    "team": team,
                    "team_code": r.get("team_code"),
                    "individual_points": 0,
                    "relay_points": 0,
                    "races": 0,
                },
            )
            if event["is_relay"]:
                if r.get("status") == "official" and r.get("points"):
                    row["relay_points"] += r["points"]
                for s in r.get("swimmers", []):
                    if s.get("athlete_key"):
                        swimmers[team].add(s["athlete_key"])
            else:
                if r.get("status") == "official":
                    row["races"] += 1
                if r.get("points"):
                    row["individual_points"] += r["points"]
                if r.get("athlete_key"):
                    swimmers[team].add(r["athlete_key"])

    scored = [
        {**row, "swimmers": len(swimmers[team]), "points": row["individual_points"] + row["relay_points"]}
        for team, row in rows.items()
    ]
    return sorted(scored, key=lambda r: (-r["points"], r["team"]))


def ordinal(n: int | None) -> str:
    if n is None:
        return "—"
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_dual_rank(result: dict, event: dict) -> str:
    if result.get("status") != "official" or not result.get("time"):
        return result.get("status") or "—"
    if event["is_open"]:
        return (
            f"{ordinal(result.get('overall_place'))}/{result.get('overall_field')} "
            f"({result.get('overall_label', 'Overall')})"
        )
    ag = (
        f"{ordinal(result.get('place'))}/{result.get('age_group_field')} "
        f"({event['age_group']})"
    )
    overall = (
        f"{ordinal(result.get('overall_place'))}/{result.get('overall_field')} "
        f"({result.get('overall_label', 'Overall')})"
    )
    return f"{ag}\n{overall}"


def _edit_distance(a: str, b: str, cap: int = 2) -> int:
    if a == b:
        return 0
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _letters(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalpha())


def _same_person(a: dict, b: dict) -> bool:
    """Conservative duplicate test for two raw athlete buckets.

    Requires a near-identical surname, a compatible given name (one a prefix of
    the other, or a single typo), a shared team, and ages within a year.
    """
    last_a, last_b = _letters(a["last_name"]), _letters(b["last_name"])
    first_a, first_b = _letters(a["first_name"]), _letters(b["first_name"])
    if not (last_a and last_b and first_a and first_b):
        return False

    last_gap = _edit_distance(last_a, last_b)
    if last_gap > 1 or (last_gap == 1 and min(len(last_a), len(last_b)) < 5):
        return False

    is_prefix = (
        first_a.startswith(first_b) or first_b.startswith(first_a)
    ) and min(len(first_a), len(first_b)) >= 3
    first_gap = _edit_distance(first_a, first_b)
    if not (first_gap == 0 or is_prefix or (first_gap == 1 and min(len(first_a), len(first_b)) >= 4)):
        return False

    if not (a["teams"] & b["teams"]):
        return False

    if a["ages"] and b["ages"]:
        if min(abs(x - y) for x in a["ages"] for y in b["ages"]) > 1:
            return False

    return True


def merge_duplicate_athletes(athletes: dict[str, dict]) -> tuple[dict[str, dict], dict[str, str]]:
    """Collapse misspelled duplicates. Returns (merged buckets, alias → canonical)."""
    keys = list(athletes)
    parent = {k: k for k in keys}

    def find(k: str) -> str:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i, ka in enumerate(keys):
        for kb in keys[i + 1 :]:
            pair = tuple(sorted((ka, kb)))
            if pair in BLOCK_MERGE:
                continue
            if pair in {tuple(sorted(p)) for p in FORCE_MERGE} or _same_person(
                athletes[ka], athletes[kb]
            ):
                union(ka, kb)

    groups: dict[str, list[str]] = defaultdict(list)
    for k in keys:
        groups[find(k)].append(k)

    merged: dict[str, dict] = {}
    alias: dict[str, str] = {}
    report: list[tuple[str, list[str]]] = []

    for members in groups.values():
        # Prefer the variant that appears most often, then the fuller given name.
        members.sort(
            key=lambda k: (
                len(athletes[k]["results"]) + len(athletes[k]["relays"]),
                len(athletes[k]["first_name"]),
                len(athletes[k]["last_name"]),
            ),
            reverse=True,
        )
        primary = athletes[members[0]]
        canonical = members[0]

        if len(members) > 1:
            report.append((primary["name"], [athletes[m]["name"] for m in members[1:]]))

        for m in members:
            alias[m] = canonical
            if m == canonical:
                continue
            other = athletes[m]
            primary["ages"] |= other["ages"]
            primary["teams"] |= other["teams"]
            primary["team_codes"] |= other["team_codes"]
            primary["results"].extend(other["results"])
            primary["relays"].extend(other["relays"])
            primary["search_names"] = sorted(
                set(primary["search_names"]) | set(other["search_names"])
            )

        merged[canonical] = primary

    for name, absorbed in sorted(report):
        print(f"  merged duplicate: {name}  <-  {', '.join(absorbed)}")

    return merged, alias


def build_athlete_index(meets: list[dict]) -> dict:
    athletes: dict[str, dict] = {}

    def ensure(name: str, age: int | None, team: str | None, team_code: str | None) -> dict:
        key = athlete_key(name)
        first, last = split_name(name)
        if key not in athletes:
            athletes[key] = {
                "key": key,
                "name": name,
                "first_name": first,
                "last_name": last,
                "search_names": sorted({name, f"{first} {last}".strip(), f"{last} {first}".strip()}),
                "ages": set(),
                "teams": set(),
                "team_codes": set(),
                "results": [],
                "relays": [],
            }
        a = athletes[key]
        if age:
            a["ages"].add(age)
        if team:
            a["teams"].add(team)
        if team_code:
            a["team_codes"].add(team_code)
        return a

    for meet in meets:
        for event in meet["events"]:
            if event["is_relay"]:
                for result in event["results"]:
                    for swimmer in result.get("swimmers", []):
                        a = ensure(
                            swimmer["name"],
                            swimmer.get("age"),
                            result.get("team"),
                            result.get("team_code"),
                        )
                        a["relays"].append(
                            {
                                "meet_id": meet["id"],
                                "meet": meet["short_name"],
                                "meet_division": meet["division"],
                                "date": meet["date"],
                                "event_code": event["code"],
                                "event_name": event["name"],
                                "event_key": event["event_key"],
                                "leg": swimmer.get("leg"),
                                "place": result.get("place"),
                                "team": result.get("team"),
                                "relay": result.get("relay"),
                                "division": result.get("division"),
                                "time": result.get("time"),
                                "time_seconds": result.get("time_seconds"),
                                "points": result.get("points"),
                                "status": result.get("status"),
                            }
                        )
                continue

            for result in event["results"]:
                a = ensure(
                    result["name"],
                    result.get("age"),
                    result.get("team"),
                    result.get("team_code"),
                )
                a["results"].append(
                    {
                        "meet_id": meet["id"],
                        "meet": meet["short_name"],
                        "meet_division": meet["division"],
                        "date": meet["date"],
                        "event_code": event["code"],
                        "event_name": event["name"],
                        "event_key": event["event_key"],
                        "gender": event["gender"],
                        "age_group": event["age_group"],
                        "distance": event["distance"],
                        "stroke": event["stroke"],
                        "is_open": event["is_open"],
                        "place": result.get("place"),
                        "age_group_field": result.get("age_group_field"),
                        "overall_place": result.get("overall_place"),
                        "overall_field": result.get("overall_field"),
                        "overall_label": result.get("overall_label"),
                        "rank_display": format_dual_rank(result, event),
                        "age": result.get("age"),
                        "team": result.get("team"),
                        "team_code": result.get("team_code"),
                        "seed": result.get("seed"),
                        "time": result.get("time"),
                        "time_seconds": result.get("time_seconds"),
                        "suspect_time": result.get("suspect_time", False),
                        "points": result.get("points"),
                        "status": result.get("status"),
                    }
                )

    athletes, alias = merge_duplicate_athletes(athletes)

    # Finalize sets → sorted lists + summary stats
    out = []
    for a in athletes.values():
        official = [r for r in a["results"] if r["status"] == "official" and r.get("time_seconds") is not None]
        age_group_places = [r["place"] for r in official if r.get("place") and not r["is_open"]]
        overall_places = [r["overall_place"] for r in official if r.get("overall_place")]
        wins = sum(1 for p in age_group_places if p == 1)
        podiums = sum(1 for p in age_group_places if p <= 3)

        # Placings and race counts stay as the meet scored them, but anything
        # derived from the clock ignores times we could not have swum.
        trusted = [r for r in official if not r.get("suspect_time")]

        # Best times by event_key
        best_by_event: dict[str, dict] = {}
        for r in trusted:
            key = r["event_key"]
            prev = best_by_event.get(key)
            if not prev or r["time_seconds"] < prev["time_seconds"]:
                best_by_event[key] = r

        # PB improvements: first official time vs best later (season progression)
        by_event_chron = defaultdict(list)
        for r in sorted(trusted, key=lambda x: x["date"]):
            by_event_chron[r["event_key"]].append(r)
        pb_events = 0
        for key, races in by_event_chron.items():
            if len(races) >= 2 and races[-1]["time_seconds"] < races[0]["time_seconds"]:
                pb_events += 1

        out.append(
            {
                "key": a["key"],
                "name": a["name"],
                "first_name": a["first_name"],
                "last_name": a["last_name"],
                "search_names": a["search_names"],
                "ages": sorted(a["ages"]),
                "teams": sorted(a["teams"]),
                "team_codes": sorted(a["team_codes"]),
                "individual_result_count": len(a["results"]),
                "relay_count": len(a["relays"]),
                "summary": {
                    "races": len(official),
                    "age_group_wins": wins,
                    "age_group_podiums": podiums,
                    "age_group_races": len(age_group_places),
                    "avg_age_group_finish": round(sum(age_group_places) / len(age_group_places), 2)
                    if age_group_places
                    else None,
                    "avg_overall_finish": round(sum(overall_places) / len(overall_places), 2)
                    if overall_places
                    else None,
                    "best_overall_finish": min(overall_places) if overall_places else None,
                    "events_improved": pb_events,
                    "best_times": {
                        k: {
                            "time": v["time"],
                            "time_seconds": v["time_seconds"],
                            "meet": v["meet"],
                            "date": v["date"],
                            "place": v["place"],
                            "age_group": v["age_group"],
                            "age_group_field": v["age_group_field"],
                            "overall_place": v["overall_place"],
                            "overall_field": v["overall_field"],
                            "overall_label": v["overall_label"],
                            "rank_display": v["rank_display"],
                        }
                        for k, v in sorted(best_by_event.items())
                    },
                },
                "results": sorted(a["results"], key=lambda r: (r["date"], r["event_code"])),
                "relays": sorted(a["relays"], key=lambda r: (r["date"], r["event_code"])),
            }
        )

    out.sort(key=lambda a: (a["last_name"].lower(), a["first_name"].lower()))
    index = {
        "generated_from_meets": [m["id"] for m in meets],
        "athlete_count": len(out),
        "athletes": out,
    }
    return index, alias


def link_meets_to_athletes(meets: list[dict], alias: dict[str, str]) -> None:
    """Stamp every meet result with the canonical athlete key so the UI can link out."""
    for meet in meets:
        for event in meet["events"]:
            for result in event["results"]:
                if event["is_relay"]:
                    for swimmer in result.get("swimmers", []):
                        raw = athlete_key(swimmer["name"])
                        swimmer["athlete_key"] = alias.get(raw, raw)
                else:
                    raw = athlete_key(result["name"])
                    result["athlete_key"] = alias.get(raw, raw)


def report_suspicious(athletes: list[dict]) -> None:
    """Surface parse artifacts (mangled names, impossible ages) instead of shipping them."""
    problems: list[str] = []
    for a in athletes:
        # Parenthesised nicknames are legitimate; digits and stray parens are not.
        if re.search(r"\d", a["name"]) or a["name"].count("(") != a["name"].count(")"):
            problems.append(f"name looks mangled: {a['name']!r}")
        for age in a["ages"]:
            if not 5 <= age <= 105:
                problems.append(f"implausible age {age} for {a['name']}")

    if problems:
        print(f"\n{len(problems)} suspicious record(s):", file=sys.stderr)
        for p in problems:
            print(f"  ! {p}", file=sys.stderr)
    else:
        print("Sanity check passed: no mangled names or implausible ages.")

    flagged = [
        (a["name"], r) for a in athletes for r in a["results"] if r.get("suspect_time")
    ]
    if flagged:
        print(f"\n{len(flagged)} time(s) flagged as impossible (kept, but not counted in records):")
        for name, r in sorted(flagged, key=lambda x: x[1]["time_seconds"]):
            print(f"  ~ {r['event_key']:14} {r['time']:>8}  {name} @ {r['meet']}")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    MEETS_DIR.mkdir(parents=True, exist_ok=True)
    meets = []
    for meta in MEET_FILES:
        print(f"Parsing {meta['pdf']} ...")
        meet = parse_meet(meta)
        print(f"  {meet['event_count']} events, {meet['result_count']} results")
        meets.append(meet)

    print("\nBuilding athlete index ...")
    _, alias = build_athlete_index(meets)
    link_meets_to_athletes(meets, alias)

    # Outlier detection needs each swimmer's full season, so it happens after
    # the first index pass; rankings and summaries are then rebuilt without the
    # times it flagged.
    flag_outlier_times(meets)
    for meet in meets:
        add_overall_rankings(meet["events"])
    athletes, alias = build_athlete_index(meets)
    link_meets_to_athletes(meets, alias)

    for meet in meets:
        out = MEETS_DIR / f"{meet['id']}.json"
        write_json(out, meet)
        print(f"Wrote {out.relative_to(ROOT)}")

    index = {
        "meets": [
            {
                "id": m["id"],
                "short_name": m["short_name"],
                "division": m["division"],
                "name": m["name"],
                "venue": m["venue"],
                "date": m["date"],
                "date_display": m["date_display"],
                "source_pdf": m["source_pdf"],
                "event_count": m["event_count"],
                "result_count": m["result_count"],
                "team_scores": meet_team_scores(m),
                "file": f"data/meets/{m['id']}.json",
            }
            for m in meets
        ]
    }
    write_json(DATA_DIR / "meets.json", index)

    write_json(DATA_DIR / "athletes.json", athletes)
    report_suspicious(athletes["athletes"])
    print(
        f"Wrote data/athletes.json ({athletes['athlete_count']} athletes)"
    )

    # Quick sanity: Voelker
    v = next((a for a in athletes["athletes"] if a["last_name"] == "Voelker"), None)
    if v:
        print("\nVoelker, Brian sanity check:")
        print(f"  individual results: {v['individual_result_count']}")
        print(f"  relays: {v['relay_count']}")
        print(f"  summary: {json.dumps(v['summary'], indent=2)[:800]}")
        for r in v["results"]:
            if r["status"] == "official":
                print(
                    f"  {r['meet']:13} {r['event_key']:16} {r['time']:>8}  "
                    f"{r['rank_display'].replace(chr(10), ' | ')}"
                )
            else:
                print(f"  {r['meet']:13} {r['event_key']:16} {r['status']}")
    else:
        print("WARNING: Voelker not found in athlete index", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
