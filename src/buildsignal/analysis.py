"""Deterministic clustering and explicit opportunity scoring."""

import hashlib
import math
import re
from collections import Counter
from datetime import UTC, datetime, timedelta

from .config import BuildSignalError

WEIGHTS = {
    "demand": 0.28,
    "breadth": 0.18,
    "recency": 0.18,
    "evidence": 0.12,
    "competition_gap": 0.16,
    "release_momentum": 0.08,
}
EXCLUDED = {"security", "private", "spam", "invalid", "duplicate", "wontfix", "wont-fix"}
STOP = set(
    "the a an is are to for of and in with on this that please add support feature bug "
    "request issue from when using does not have it be can should would new".split()
)
ALIASES = {
    "tools": "tool",
    "calls": "call",
    "models": "model",
    "agents": "agent",
    "caching": "cache",
    "cached": "cache",
    "caches": "cache",
    "schemas": "schema",
}


def date(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def tokens(text):
    words = re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower())
    return set(ALIASES.get(w, w) for w in words if w not in STOP)


def normalize(name, rows, kind, as_of, days):
    out = []
    since = as_of - timedelta(days=days)
    for item in rows:
        if not isinstance(item, dict):
            continue
        labels = {
            str(x.get("name", "") if isinstance(x, dict) else x).lower()
            for x in item.get("labels", [])
        }
        if kind == "issue" and (
            "pull_request" in item or item.get("state") == "closed" or EXCLUDED & labels
        ):
            continue
        if kind == "release" and item.get("draft"):
            continue
        try:
            updated = date(
                item.get("published_at") if kind == "release" else item.get("updated_at", "")
            )
        except (ValueError, TypeError, AttributeError):
            continue
        if not since <= updated <= as_of:
            continue
        number = item.get("number") if kind == "issue" else item.get("id")
        if type(number) is not int or number < 1:
            continue
        # Construct evidence URLs; do not trust arbitrary URLs in issue/fixture text.
        route = f"issues/{number}" if kind == "issue" else "releases"
        url = f"https://github.com/{name}/{route}"
        if kind == "release":
            candidate = str(item.get("html_url", ""))
            if candidate.startswith(f"https://github.com/{name}/releases/"):
                url = candidate
        out.append(
            {
                "id": f"{name}:{kind}:{number}",
                "repository": name,
                "kind": kind,
                "title": str(item.get("title") or item.get("name") or "Untitled")[:300],
                "body": str(item.get("body") or "")[:1200],
                "url": url,
                "updated_at": updated.isoformat(),
                "labels": sorted(labels),
                "comments": max(0, int(item.get("comments") or 0)),
                "reactions": max(0, int((item.get("reactions") or {}).get("total_count", 0))),
            }
        )
    return out


def collect(client, config, as_of):
    signals = []
    scan = config["scan"]
    for name in config["repositories"]:
        client.public_repository(name)
        for kind, plural, limit in [
            ("issue", "issues", scan["max_issues"]),
            ("release", "releases", scan["max_releases"]),
        ]:
            rows = client.items(
                name, plural, limit, (as_of - timedelta(days=scan["days"])).isoformat()
            )
            signals.extend(normalize(name, rows, kind, as_of, scan["days"]))
    return sorted({s["id"]: s for s in signals}.values(), key=lambda s: s["id"])


def cluster(signals, threshold=0.28):
    issues = sorted([s for s in signals if s["kind"] == "issue"], key=lambda s: s["id"])
    parent = list(range(len(issues)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    title = [tokens(s["title"]) for s in issues]
    full = [tokens(s["title"] + " " + s["body"]) for s in issues]
    for i in range(len(issues)):
        for j in range(i):
            shared = len(title[i] & title[j])
            sim = (
                0.68 * shared / max(1, len(title[i] | title[j]))
                + 0.32 * len(full[i] & full[j]) / max(1, len(full[i] | full[j]))
                + min(0.24, shared * 0.08)
            )
            cutoff = threshold + (0.07 if issues[i]["repository"] == issues[j]["repository"] else 0)
            if shared and sim >= cutoff:
                parent[root(i)] = root(j)
    groups = {}
    for i, issue in enumerate(issues):
        groups.setdefault(root(i), []).append(issue)
    result = []
    for members in groups.values():
        counts = Counter()
        for issue in members:
            counts.update(list(tokens(issue["title"])) * 3)
            counts.update(tokens(issue["body"]))
        keywords = [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]
        releases = [
            s
            for s in signals
            if s["kind"] == "release"
            and s["repository"] in {i["repository"] for i in members}
            and len(tokens(s["title"] + " " + s["body"]) & set(keywords)) >= 2
        ]
        identifier = hashlib.sha256("\n".join(i["id"] for i in members).encode()).hexdigest()[:12]
        best = sorted(members, key=lambda s: (-s["comments"] - s["reactions"], s["id"]))[0]
        result.append(
            {
                "id": identifier,
                "title": best["title"],
                "issues": members,
                "releases": sorted(releases, key=lambda s: s["id"])[:5],
                "keywords": keywords,
            }
        )
    return sorted(result, key=lambda g: g["id"])


def score(group, as_of, competition):
    issues = group["issues"]
    engagement = sum(1 + s["comments"] + 1.5 * s["reactions"] for s in issues)
    components = {
        "demand": min(100, 30 * math.log1p(engagement)),
        "breadth": min(100, 25 * len({s["repository"] for s in issues})),
        "recency": sum(
            100 * 2 ** (-max(0, (as_of - date(s["updated_at"])).total_seconds()) / 86400 / 30)
            for s in issues
        )
        / len(issues),
        "evidence": sum(
            25
            + (25 if len(s["body"]) >= 80 else 0)
            + (25 if s["labels"] else 0)
            + (25 if s["comments"] or s["reactions"] else 0)
            for s in issues
        )
        / len(issues),
        "competition_gap": 50
        if competition is None
        else max(5, 100 - 19 * math.log1p(max(0, competition["total_count"]))),
        "release_momentum": min(100, 20 + 35 * len(group["releases"])),
    }
    values = {k: round(v, 2) for k, v in components.items()}
    return round(sum(values[k] * w for k, w in WEIGHTS.items()), 2), values


def rank(groups, client, config, as_of, check_competition=True):
    warnings = []
    output = []
    preliminary = sorted(groups, key=lambda g: (-score(g, as_of, None)[0], g["id"]))
    cap = config["scan"]["max_opportunities"]
    for group in preliminary[: cap * 2]:
        competition = None
        if check_competition and group["keywords"]:
            try:
                competition = client.competition(group["keywords"])
            except BuildSignalError as exc:
                warnings.append(f"Competition unverified for {group['id']}: {exc}")
        value, components = score(group, as_of, competition)
        if value >= config["scan"]["minimum_score"]:
            output.append(
                group
                | {
                    "score": value,
                    "components": components,
                    "competition": competition,
                    "enriched": False,
                    "brief": {
                        "problem": group["title"],
                        "proposed_v1": [
                            "Reproduce the linked issues with deterministic fixtures.",
                            "Implement one narrow workflow that resolves the repeated friction.",
                            "Compare maintained competitors before committing to scope.",
                        ],
                        "validation": [
                            "Validate the need with affected maintainers.",
                            "Publish a runnable before/after example.",
                        ],
                    },
                }
            )
    return sorted(output, key=lambda g: (-g["score"], g["id"]))[:cap], warnings
